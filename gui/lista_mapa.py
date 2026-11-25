from typing import Any, Callable

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from ..layers.orden import clave_de_fila
from ..layers.proyecto import GRUPO_PROPERTY
from ..model.tree import clean_label, find_node
from ..theme import icono_asset, set_role

Fila = tuple[str, str, bool]

ANCHO_TARJETA: int = 372

MARGEN_TARJETA: int = 12

RELLENO_NOMBRE: int = 16

LADO_CONTADOR: int = 18

LADO_ACCION: int = 22

AYUDA_FILA: str = 'Clic para ver sus acciones, su periodo y su leyenda, y ubicarla en el catálogo.'


def capas_en_mapa(arbol: list[dict[str, Any]]) -> list[Fila]:
    filas: list[Fila] = []
    vistas: set[str] = set()
    for nodo in QgsProject.instance().layerTreeRoot().findLayers():
        capa = nodo.layer()
        if capa is None:
            continue
        grupo = str(capa.customProperty(GRUPO_PROPERTY) or '')
        clave = clave_de_fila(capa)
        if not clave or clave in vistas:
            continue
        vistas.add(clave)
        nodo = find_node(arbol, clave)
        etiqueta = clean_label(nodo.get('label') or '') if nodo else capa.name()
        filas.append((clave, etiqueta, bool(grupo)))
    return filas


class Nombre(QPushButton):

    def __init__(self, texto: str) -> None:
        super().__init__(texto)
        self._completo = texto
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def resizeEvent(self, evento: Any) -> None:
        super().resizeEvent(evento)
        ancho = max(0, self.width() - RELLENO_NOMBRE)
        self.setText(self.fontMetrics().elidedText(
            self._completo, Qt.TextElideMode.ElideRight, ancho))


def boton(texto: str, ayuda: str, rol: str, al_clic: Callable[[], Any]) -> QPushButton:
    nuevo = QPushButton(texto)
    nuevo.setToolTip(ayuda)
    nuevo.clicked.connect(al_clic)
    set_role(nuevo, rol)
    return nuevo


def accion(normal: str, hover: str, ayuda: str, al_clic: Callable[[], Any]) -> QToolButton:
    nuevo = QToolButton()
    nuevo.setIcon(icono_asset(normal, hover))
    nuevo.setIconSize(QSize(LADO_ACCION, LADO_ACCION))
    nuevo.setAutoRaise(True)
    nuevo.setToolTip(ayuda)
    nuevo.setCursor(Qt.CursorShape.PointingHandCursor)
    nuevo.clicked.connect(al_clic)
    set_role(nuevo, 'mapa-accion')
    return nuevo


def _limpiar(total: int, al_limpiar: Callable[[], Any]) -> QToolButton:
    limpiar = accion('eliminar-hover.svg', 'eliminar-rojo-hover.svg',
                     'Quitar todas las capas del mapa', lambda: None)
    texto = f'Quitar {"la capa" if total == 1 else f"las {total} capas"} del mapa'
    menu = QMenu(limpiar)
    menu.addAction(texto, al_limpiar)
    limpiar.setMenu(menu)
    limpiar.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    limpiar.setFixedSize(LADO_ACCION + 14, LADO_ACCION + 10)
    contador = QLabel(str(total), limpiar)
    contador.setAlignment(Qt.AlignmentFlag.AlignCenter)
    contador.setFixedSize(LADO_CONTADOR, LADO_CONTADOR)
    contador.move(limpiar.width() - LADO_CONTADOR, 0)
    contador.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    set_role(contador, 'mapa-contador')
    return limpiar


def encabezado(total: int, minimizada: bool, al_alternar: Callable[[], Any],
               al_limpiar: Callable[[], Any], switch: QWidget) -> QWidget:
    caja = QWidget()
    layout = QHBoxLayout(caja)
    layout.setContentsMargins(0, 0, 0, 0 if minimizada else 8)
    layout.setSpacing(4)
    titulo = QLabel('Capa seleccionada' if total == 1 else 'Capas seleccionadas')
    set_role(titulo, 'mapa-titulo')
    centro = Qt.AlignmentFlag.AlignVCenter
    layout.addWidget(titulo, 0, centro)
    layout.addStretch(1)
    layout.addWidget(switch, 0, centro)
    layout.addWidget(_limpiar(total, al_limpiar), 0, centro)
    layout.addWidget(boton('+' if minimizada else '−',
                           'Expandir' if minimizada else 'Minimizar',
                           'mapa-minimizar', al_alternar), 0, centro)
    return caja


def vaciar(layout: Any) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout() is not None:
            vaciar(item.layout())
