from typing import Any, Callable, Optional

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QIcon
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

LADO_BOTON_ACCION: int = 34

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


def boton_accion(icono: QIcon, ayuda: str, al_clic: Callable[[], Any]) -> QToolButton:
    nuevo = QToolButton()
    nuevo.setIcon(icono)
    nuevo.setIconSize(QSize(LADO_ACCION, LADO_ACCION))
    nuevo.setFixedSize(LADO_BOTON_ACCION, LADO_BOTON_ACCION)
    nuevo.setAutoRaise(True)
    nuevo.setToolTip(ayuda)
    nuevo.setCursor(Qt.CursorShape.PointingHandCursor)
    nuevo.clicked.connect(al_clic)
    set_role(nuevo, 'mapa-accion')
    return nuevo


def accion(archivo: str, ayuda: str, al_clic: Callable[[], Any],
           hover: Optional[str] = None) -> QToolButton:
    return boton_accion(icono_asset(archivo, hover), ayuda, al_clic)


def contador_en(boton: QToolButton, total: int) -> QLabel:
    contador = QLabel(str(total), boton)
    contador.setAlignment(Qt.AlignmentFlag.AlignCenter)
    contador.setFixedSize(LADO_CONTADOR, LADO_CONTADOR)
    contador.move(boton.width() - LADO_CONTADOR, 0)
    contador.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
    set_role(contador, 'mapa-contador')
    return contador


def bote(ayuda: str, al_clic: Callable[[], Any]) -> QToolButton:
    return accion('eliminar-hover.svg', ayuda, al_clic, 'eliminar-rojo-hover.svg')


def _limpiar(total: int, al_limpiar: Callable[[], Any]) -> QToolButton:
    limpiar = bote('Quitar todas las capas del mapa', lambda: None)
    texto = f'Quitar {"la capa" if total == 1 else f"las {total} capas"} del mapa'
    menu = QMenu(limpiar)
    menu.addAction(texto, al_limpiar)
    limpiar.setMenu(menu)
    limpiar.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    contador_en(limpiar, total)
    return limpiar


AYUDA_MINIMIZAR: str = 'Minimizar a un icono'


def encabezado(total: int, al_limpiar: Callable[[], Any], switch: QWidget,
               al_minimizar: Callable[[], Any]) -> QWidget:
    caja = QWidget()
    layout = QHBoxLayout(caja)
    layout.setContentsMargins(0, 0, 0, 8)
    layout.setSpacing(4)
    titulo = QLabel('Capa seleccionada' if total == 1 else 'Capas seleccionadas')
    set_role(titulo, 'mapa-titulo-capas')
    centro = Qt.AlignmentFlag.AlignVCenter
    layout.addWidget(titulo, 0, centro)
    layout.addStretch(1)
    layout.addWidget(switch, 0, centro)
    layout.addWidget(_limpiar(total, al_limpiar), 0, centro)
    layout.addWidget(accion('minimizar.svg', AYUDA_MINIMIZAR, al_minimizar), 0, centro)
    return caja


def vaciar(layout: Any) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout() is not None:
            vaciar(item.layout())
