from typing import Any, Optional

from qgis.PyQt.QtCore import QByteArray
from qgis.PyQt.QtGui import QIcon, QImage, QPixmap
from qgis.PyQt.QtWidgets import QToolButton

from ..api.client import MapaLabClient
from ..assets_cache import fetch_asset
from ..identidad import tema_icono_urls, tema_override_url
from ..model.tree import alias_de_tema
from ..theme import icono_refrescar
from .lista_mapa import boton_accion

ICON_SIZE: int = 20

TEMA_ICON_SIZE: int = 34

_memoria: dict[str, Optional[QIcon]] = {}


def _desde_svg(datos: bytes, tamano: int = ICON_SIZE) -> Optional[QIcon]:
    try:
        from qgis.PyQt.QtSvg import QSvgRenderer
    except ImportError:
        return None

    renderer = QSvgRenderer(QByteArray(datos))
    if not renderer.isValid():
        return None

    from qgis.PyQt.QtGui import QPainter
    imagen = QImage(tamano, tamano, QImage.Format.Format_ARGB32)
    imagen.fill(0)
    painter = QPainter(imagen)
    renderer.render(painter)
    painter.end()
    return QIcon(QPixmap.fromImage(imagen))


def _desde_raster(datos: bytes, tamano: int = ICON_SIZE) -> Optional[QIcon]:
    pixmap = QPixmap()
    if not pixmap.loadFromData(datos):
        return None
    return QIcon(pixmap.scaledToHeight(tamano))


def icono_de_url(client: MapaLabClient, url: str,
                 tamano: int = ICON_SIZE) -> Optional[QIcon]:
    if not url:
        return None
    clave = f'{url}:{tamano}'
    if clave in _memoria:
        return _memoria[clave]

    datos = fetch_asset(client, [url], solo_cache=True)
    icono: Optional[QIcon] = None
    if datos:
        es_svg = b'<svg' in datos[:400]
        icono = _desde_svg(datos, tamano) if es_svg else _desde_raster(datos, tamano)

    _memoria[clave] = icono
    return icono


def icono_de_tema(client: MapaLabClient, node: dict[str, Any],
                  hover: bool = False) -> Optional[QIcon]:
    alias = alias_de_tema(node)
    if not alias:
        return None

    clave = f'{alias}:hover' if hover else alias
    if clave in _memoria:
        return _memoria[clave]

    datos = fetch_asset(client, tema_icono_urls(alias, hover), solo_cache=True)
    icono = _desde_svg(datos, TEMA_ICON_SIZE) if datos and b'<svg' in datos[:400] else None
    if icono is None and hover:
        icono = icono_de_tema(client, node, hover=False)

    _memoria[clave] = icono
    return icono


def olvidar_iconos() -> None:
    _memoria.clear()


def boton_de_recarga(al_pulsar: Any) -> QToolButton:
    return boton_accion(icono_refrescar(), 'Recargar catálogo', al_pulsar)


def icono_de_nodo(client: MapaLabClient, node: dict[str, Any],
                  es_raiz: bool = False, hover: bool = False) -> Optional[QIcon]:
    url = node.get('iconUrl')
    if isinstance(url, str) and url:
        return icono_de_url(client, url, TEMA_ICON_SIZE if es_raiz else ICON_SIZE)
    propio = tema_override_url(node, hover) if es_raiz else ''
    if propio:
        return icono_de_url(client, propio, TEMA_ICON_SIZE)
    if es_raiz:
        return icono_de_tema(client, node, hover)
    return None
