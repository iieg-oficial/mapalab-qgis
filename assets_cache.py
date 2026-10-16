import hashlib
import os
from typing import Optional

from qgis.core import QgsFeedback

from .almacen import carpeta, edad_s, escribir_atomico, leer
from .api.client import MapaLabCancelado, MapaLabClient, MapaLabError
from .config import ASSET_MISS_TTL_S, ASSET_TIMEOUT_MS, ASSET_TTL_S, es_del_servidor

CACHE_DIR: str = 'assets'

MISS_SUFIJO: str = '.miss'


def _ruta(url: str) -> str:
    digest = hashlib.sha1(url.encode('utf-8'), usedforsecurity=False).hexdigest()[:16]
    extension = os.path.splitext(url.split('?')[0])[1][:6] or '.bin'
    return os.path.join(carpeta(CACHE_DIR), f'{digest}{extension}')


def _vigente(path: str, ttl_s: int) -> bool:
    edad = edad_s(path)
    return edad is not None and edad < ttl_s


def _cacheado(url: str, aceptar_viejo: bool) -> Optional[bytes]:
    path = _ruta(url)
    if not aceptar_viejo and not _vigente(path, ASSET_TTL_S):
        return None
    return leer(path) or None


def _fallo_reciente(url: str) -> bool:
    return _vigente(_ruta(url) + MISS_SUFIJO, ASSET_MISS_TTL_S)


def _descargar(client: MapaLabClient, url: str,
               feedback: Optional[QgsFeedback] = None) -> Optional[bytes]:
    try:
        status, content, _ = client.request(
            url, timeout_ms=ASSET_TIMEOUT_MS, feedback=feedback)
    except MapaLabCancelado:
        raise
    except MapaLabError:
        return None
    if (status and status >= 400) or not content:
        return None
    return content


def candidatas(urls: list[str]) -> list[str]:
    return [url for url in urls if url and es_del_servidor(url)]


def fetch_asset(client: MapaLabClient, urls: list[str],
                feedback: Optional[QgsFeedback] = None,
                solo_cache: bool = False) -> Optional[bytes]:
    lista = candidatas(urls)
    if not lista:
        return None

    for url in lista:
        vigente = _cacheado(url, aceptar_viejo=solo_cache)
        if vigente:
            return vigente

    if solo_cache:
        return None

    for url in lista:
        if feedback is not None and feedback.isCanceled():
            return None
        if _fallo_reciente(url):
            continue
        datos = _descargar(client, url, feedback)
        if datos:
            escribir_atomico(_ruta(url), datos)
            return datos
        escribir_atomico(_ruta(url) + MISS_SUFIJO, b'')

    for url in lista:
        viejo = _cacheado(url, aceptar_viejo=True)
        if viejo:
            return viejo
    return None
