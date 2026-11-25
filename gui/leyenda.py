from typing import Any, Callable, Optional

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QImage, QPixmap
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from ..layers.orden import nodos_de_fila
from ..theme import set_role

ANCHO_LEYENDA: int = 300

ALTO_MAXIMO: int = 320

LADO_ICONO: int = 16


def _pixmap(decoracion: Any) -> Optional[QPixmap]:
    if isinstance(decoracion, QPixmap) and not decoracion.isNull():
        return decoracion
    if isinstance(decoracion, QImage) and not decoracion.isNull():
        return QPixmap.fromImage(decoracion)
    if isinstance(decoracion, QIcon) and not decoracion.isNull():
        return decoracion.pixmap(LADO_ICONO, LADO_ICONO)
    return None


def _ajustar(pixmap: QPixmap) -> QPixmap:
    if pixmap.width() <= ANCHO_LEYENDA:
        return pixmap
    return pixmap.scaledToWidth(ANCHO_LEYENDA, Qt.TransformationMode.SmoothTransformation)


def _renglon(pieza: Any, omitir: str) -> Optional[QWidget]:
    pixmap = _pixmap(pieza.data(Qt.ItemDataRole.DecorationRole))
    texto = str(pieza.data(Qt.ItemDataRole.DisplayRole) or '')
    if texto == omitir:
        texto = ''
    if pixmap is None and not texto:
        return None
    caja = QWidget()
    renglon = QHBoxLayout(caja)
    renglon.setContentsMargins(0, 0, 0, 0)
    renglon.setSpacing(6)
    if pixmap is not None:
        imagen = QLabel()
        imagen.setPixmap(_ajustar(pixmap))
        set_role(imagen, 'mapa-leyenda-texto')
        renglon.addWidget(imagen, 0, Qt.AlignmentFlag.AlignTop)
    if texto:
        etiqueta = QLabel(texto)
        etiqueta.setWordWrap(True)
        set_role(etiqueta, 'mapa-leyenda-texto')
        renglon.addWidget(etiqueta, 1)
    else:
        renglon.addStretch(1)
    return caja


class Leyendas:

    def __init__(self, vista: Callable[[], Any], al_cambiar: Callable[[], None]) -> None:
        self._vista = vista
        self._al_cambiar = al_cambiar
        self._conectadas: set[int] = set()

    def _piezas(self, nodo: Any) -> list[Any]:
        vista = self._vista()
        modelo = vista.layerTreeModel() if vista is not None else None
        if modelo is None:
            return []
        piezas = list(modelo.layerLegendNodes(nodo, False))
        for pieza in piezas:
            if id(pieza) not in self._conectadas:
                self._conectadas.add(id(pieza))
                pieza.dataChanged.connect(self._al_cambiar)
        return piezas

    def de(self, clave: str) -> Optional[QWidget]:
        nodos = nodos_de_fila(clave)
        contenido = QWidget()
        set_role(contenido, 'mapa-leyenda')
        layout = QVBoxLayout(contenido)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        hay = False
        for nodo in nodos:
            nombre = nodo.layer().name()
            renglones = [renglon for renglon in (
                _renglon(pieza, nombre) for pieza in self._piezas(nodo)) if renglon is not None]
            if not renglones:
                continue
            if len(nodos) > 1:
                subtitulo = QLabel(nombre)
                set_role(subtitulo, 'mapa-leyenda-subtitulo')
                layout.addWidget(subtitulo)
            for renglon in renglones:
                layout.addWidget(renglon)
            hay = True
        if not hay:
            return None
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        set_role(scroll, 'mapa-lista')
        scroll.setWidget(contenido)
        scroll.setFixedHeight(min(contenido.sizeHint().height(), ALTO_MAXIMO))
        return scroll
