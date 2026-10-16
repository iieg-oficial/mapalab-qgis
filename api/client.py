import json
import os
import re
from typing import Any, Callable, Optional
from urllib.parse import urlencode

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import QgsBlockingNetworkRequest, QgsFeedback

from ..almacen import carpeta_del_servidor, escribir_atomico, leer
from ..config import (
    CLIENT_HEADER,
    CLIENT_VALUE,
    ETAG_CACHE_FILE,
    REQUEST_TIMEOUT_MS,
    TREE_CACHE_FILE,
    api_url,
    get_base_url,
)


class MapaLabError(Exception):
    pass


class MapaLabCancelado(MapaLabError):
    pass


def _describe(content: bytes) -> str:
    text = content[:400].decode('utf-8', errors='replace').strip()
    if not text:
        return 'Respuesta vacía.'
    if text.lstrip().lower().startswith(('<!doctype', '<html')):
        title = re.search(r'<title[^>]*>(.*?)</title>', text, re.IGNORECASE | re.DOTALL)
        detail = title.group(1).strip() if title else 'sin título'
        return f'Llegó una página HTML ({detail}).'
    return f'Empieza con: {text[:120]!r}'


def _read_cache(carpeta: str, name: str) -> Optional[str]:
    datos = leer(os.path.join(carpeta, name))
    if not datos:
        return None
    return datos.decode('utf-8', errors='replace')


def _write_cache(carpeta: str, name: str, content: bytes) -> None:
    escribir_atomico(os.path.join(carpeta, name), content)


def _parse_tree(texto: Optional[str]) -> Optional[list[dict[str, Any]]]:
    if not texto:
        return None
    try:
        payload = json.loads(texto)
    except ValueError:
        return None
    return payload if isinstance(payload, list) else None


class MapaLabClient:

    def __init__(self) -> None:
        self._tree: Optional[list[dict[str, Any]]] = None
        self.desde_cache: bool = False

    def olvidar(self) -> None:
        self._tree = None
        self.desde_cache = False

    def request(self, url: str, etag: Optional[str] = None,
                timeout_ms: int = REQUEST_TIMEOUT_MS,
                feedback: Optional[QgsFeedback] = None,
                on_progress: Optional[Callable[[int, int], None]] = None,
                ) -> tuple[int, bytes, Optional[str]]:
        if not get_base_url():
            raise MapaLabError('Falta configurar la dirección de MapaLab.')

        request = QNetworkRequest(QUrl(url))
        request.setRawHeader(CLIENT_HEADER, CLIENT_VALUE)
        request.setTransferTimeout(timeout_ms)
        if etag:
            request.setRawHeader(b'If-None-Match', etag.encode('utf-8'))

        blocking = QgsBlockingNetworkRequest()
        if on_progress is not None:
            blocking.downloadProgress.connect(on_progress)
        error = blocking.get(request, forceRefresh=True, feedback=feedback)

        if feedback is not None and feedback.isCanceled():
            raise MapaLabCancelado('Operación cancelada.')

        reply = blocking.reply()
        status = int(reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) or 0)
        content = bytes(reply.content())

        if error != QgsBlockingNetworkRequest.NoError and status != 304:
            if status >= 400:
                raise MapaLabError(f'El servidor respondió {status}. {_describe(content)}')
            raise MapaLabError(blocking.errorMessage() or 'Error de red')

        raw_etag = reply.rawHeader(b'ETag')
        new_etag = bytes(raw_etag).decode('utf-8') if raw_etag else None
        return status, content, new_etag

    def _decode_json(self, status: int, content: bytes, label: str) -> Any:
        if status and status >= 400:
            raise MapaLabError(f'{label}: el servidor respondió {status}. {_describe(content)}')
        if not content.strip():
            raise MapaLabError(
                f'{label}: el servidor respondió {status or "sin estado"} y sin contenido. '
                'Revisa la dirección y que el certificado esté aceptado.')
        try:
            return json.loads(content.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MapaLabError(
                f'{label}: la respuesta no es JSON ({status}). {_describe(content)}') from exc

    def _get_json(self, path: str, params: dict[str, str],
                  feedback: Optional[QgsFeedback] = None) -> Any:
        url = f'{api_url(path)}?{urlencode(params)}' if params else api_url(path)
        status, content, _ = self.request(url, feedback=feedback)
        return self._decode_json(status, content, path)

    def fetch_tree(self, force: bool = False,
                   feedback: Optional[QgsFeedback] = None) -> list[dict[str, Any]]:
        if self._tree is not None and not force:
            return self._tree

        carpeta = carpeta_del_servidor()
        cached_etag = _read_cache(carpeta, ETAG_CACHE_FILE)
        cached_tree = _parse_tree(_read_cache(carpeta, TREE_CACHE_FILE))
        url = api_url('/layers/tree')

        try:
            status, content, etag = self.request(
                url, etag=cached_etag if cached_tree else None, feedback=feedback)
        except MapaLabCancelado:
            raise
        except MapaLabError:
            if cached_tree is not None:
                self._tree, self.desde_cache = cached_tree, True
                return self._tree
            raise

        if status == 304 and cached_tree is not None:
            self._tree, self.desde_cache = cached_tree, False
            return self._tree

        arbol = self._decode_json(status, content, 'Catálogo de capas')
        if not isinstance(arbol, list):
            raise MapaLabError('Catálogo de capas: la respuesta no es una lista de nodos.')
        self._tree, self.desde_cache = arbol, False
        _write_cache(carpeta, TREE_CACHE_FILE, content)
        if etag:
            _write_cache(carpeta, ETAG_CACHE_FILE, etag.encode('utf-8'))
        return self._tree

    def fetch_text(self, url: str, feedback: Optional[QgsFeedback] = None) -> str:
        _, content, _ = self.request(url, feedback=feedback)
        return content.decode('utf-8', errors='replace')

    def fetch_metadata(self, workspace: str, layer: str,
                       feedback: Optional[QgsFeedback] = None) -> Any:
        return self._get_json(
            '/metadata/', {'workspace': workspace, 'layer': layer}, feedback=feedback)

    def fetch_periodicity(self, workspace: str, layer: str) -> dict[str, Any]:
        payload = self._get_json('/periodicity/', {'workspace': workspace, 'layer': layer})
        if isinstance(payload, dict):
            return payload.get('periodicity') or {}
        return {}

    def fetch_municipios(self) -> list[dict[str, Any]]:
        payload = self._get_json('/municipios/', {})
        if isinstance(payload, dict):
            return payload.get('items') or []
        return []

    def descargar(self, url: str, timeout_ms: int,
                  feedback: Optional[QgsFeedback] = None,
                  on_progress: Optional[Callable[[int, int], None]] = None) -> bytes:
        _, content, _ = self.request(
            url, timeout_ms=timeout_ms, feedback=feedback, on_progress=on_progress)
        return content
