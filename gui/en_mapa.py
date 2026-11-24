from typing import Any, Callable, Optional

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QEvent, QObject, Qt, QTimer
from qgis.PyQt.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..config import NODE_ID_PROPERTY
from ..layers.grupos import quitar_grupo
from ..layers.proyecto import GRUPO_PROPERTY
from ..model.tree import clean_label, find_node
from ..theme import apply_theme, set_role, sombra

Fila = tuple[str, str, bool]

FILAS_PANEL: int = 3


ANCHO_TARJETA: int = 280

MARGEN_TARJETA: int = 12

RELLENO_NOMBRE: int = 16

ALTO_FILA: int = 34

ESPACIO_COLUMNAS: int = 8

AYUDA_FILA: str = 'Clic para ubicarla en el catálogo; la ✕ la quita del mapa.'


def capas_en_mapa(arbol: list[dict[str, Any]]) -> list[Fila]:
    filas: list[Fila] = []
    vistas: set[str] = set()
    for nodo in QgsProject.instance().layerTreeRoot().findLayers():
        capa = nodo.layer()
        if capa is None:
            continue
        grupo = str(capa.customProperty(GRUPO_PROPERTY) or '')
        clave = grupo or str(capa.customProperty(NODE_ID_PROPERTY) or '')
        if not clave or clave in vistas:
            continue
        vistas.add(clave)
        nodo_grupo = find_node(arbol, grupo) if grupo else None
        etiqueta = clean_label(nodo_grupo.get('label') or '') if nodo_grupo else capa.name()
        filas.append((clave, etiqueta, bool(grupo)))
    return filas


class _Nombre(QPushButton):

    def __init__(self, texto: str) -> None:
        super().__init__(texto)
        self._completo = texto
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)

    def resizeEvent(self, evento: Any) -> None:
        super().resizeEvent(evento)
        ancho = max(0, self.width() - RELLENO_NOMBRE)
        self.setText(self.fontMetrics().elidedText(
            self._completo, Qt.TextElideMode.ElideRight, ancho))


def _titulo(total: int) -> QWidget:
    caja = QWidget()
    layout = QHBoxLayout(caja)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(6)
    titulo = QLabel('Capa seleccionada' if total == 1 else 'Capas seleccionadas')
    set_role(titulo, 'mapa-titulo')
    contador = QLabel(str(total))
    contador.setAlignment(Qt.AlignmentFlag.AlignCenter)
    set_role(contador, 'mapa-contador')
    layout.addWidget(titulo)
    layout.addWidget(contador)
    layout.addStretch(1)
    return caja


class _Lista(QWidget):

    def __init__(self, al_elegir: Callable[[str], None], al_quitar: Callable[[Fila], None],
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._al_elegir = al_elegir
        self._al_quitar = al_quitar
        self.setVisible(False)

    def _nombre(self, fila: Fila) -> QPushButton:
        nombre = _Nombre(fila[1])
        nombre.setToolTip(f'{fila[1]}\n{AYUDA_FILA}')
        nombre.clicked.connect(lambda: self._al_elegir(fila[0]))
        set_role(nombre, 'mapa-capa')
        return nombre

    def _quitar(self, fila: Fila, rol: str) -> QPushButton:
        quitar = QPushButton('✕')
        quitar.setToolTip('Quitar del mapa')
        quitar.clicked.connect(lambda: self._al_quitar(fila))
        set_role(quitar, rol)
        return quitar


def _vaciar(layout: Any) -> None:
    while layout.count():
        item = layout.takeAt(0)
        if item.widget() is not None:
            item.widget().deleteLater()


class TarjetaEnMapa(_Lista):

    def __init__(self, al_elegir: Callable[[str], None], al_quitar: Callable[[Fila], None],
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(al_elegir, al_quitar, parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 8, 10)
        self._layout.setSpacing(2)
        set_role(self, 'mapa-tarjeta')

    def refrescar(self, filas: list[Fila]) -> None:
        _vaciar(self._layout)
        self._layout.addWidget(_titulo(len(filas)))
        for fila in filas:
            caja = QWidget()
            renglon = QHBoxLayout(caja)
            renglon.setContentsMargins(0, 0, 0, 0)
            renglon.addWidget(self._nombre(fila), 1)
            renglon.addWidget(self._quitar(fila, 'mapa-quitar'))
            self._layout.addWidget(caja)
        self.setVisible(bool(filas))
        QTimer.singleShot(0, self._ajustar)

    def _ajustar(self) -> None:
        self.setFixedHeight(self.sizeHint().height())


class PanelEnMapa(_Lista):

    def __init__(self, al_elegir: Callable[[str], None],
                 al_quitar: Callable[[Fila], None]) -> None:
        super().__init__(al_elegir, al_quitar)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        set_role(self._scroll, 'mapa-lista')
        contenido = QWidget()
        set_role(contenido, 'mapa-lista')
        self._grid = QGridLayout(contenido)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setHorizontalSpacing(ESPACIO_COLUMNAS)
        self._grid.setVerticalSpacing(0)
        self._grid.setColumnStretch(0, 1)
        self._scroll.setWidget(contenido)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._scroll)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def refrescar(self, filas: list[Fila]) -> None:
        _vaciar(self._grid)
        fondo = QWidget()
        set_role(fondo, 'mapa-fondo')
        self._grid.addWidget(fondo, 0, 0, len(filas) + 2, 1)
        titulo = _titulo(len(filas))
        titulo.setContentsMargins(12, 10, 12, 4)
        self._grid.addWidget(titulo, 0, 0)
        for indice, fila in enumerate(filas, start=1):
            caja = QWidget()
            renglon = QHBoxLayout(caja)
            renglon.setContentsMargins(10, 0, 8, 0)
            renglon.addWidget(self._nombre(fila))
            caja.setFixedHeight(ALTO_FILA)
            self._grid.addWidget(caja, indice, 0)
            quitar = self._quitar(fila, 'mapa-quitar-fuera')
            quitar.setFixedSize(ALTO_FILA, ALTO_FILA)
            self._grid.addWidget(quitar, indice, 1)
        self._grid.setRowMinimumHeight(len(filas) + 1, 8)
        visibles = min(len(filas), FILAS_PANEL)
        alto = titulo.sizeHint().height() + visibles * ALTO_FILA + 8
        self.setFixedHeight(alto)
        self.setVisible(bool(filas))


class _Anclar(QObject):

    def __init__(self, tarjeta: QWidget, canvas: QWidget) -> None:
        super().__init__(tarjeta)
        self._tarjeta = tarjeta
        canvas.installEventFilter(self)

    def eventFilter(self, objeto: QObject, evento: Any) -> bool:
        if evento.type() == QEvent.Type.Resize:
            self._tarjeta.move(MARGEN_TARJETA, MARGEN_TARJETA)
        return False


class EnMapa:

    def __init__(self, canvas: Any, arbol: Any, obtener_arbol: Callable[[], list],
                 quitar_nodo: Callable[[str], Any]) -> None:
        self._arbol = arbol
        self._obtener_arbol = obtener_arbol
        self._quitar_nodo = quitar_nodo
        self.panel = PanelEnMapa(self._elegir, self._quitar)
        self._espera = QTimer(self.panel)
        self._espera.setSingleShot(True)
        self._espera.timeout.connect(self._pintar)
        self._tarjeta: Optional[TarjetaEnMapa] = None
        if canvas is not None:
            self._tarjeta = TarjetaEnMapa(self._elegir, self._quitar, canvas)
            self._tarjeta.setFixedWidth(ANCHO_TARJETA)
            apply_theme(self._tarjeta)
            sombra(self._tarjeta).setEnabled(True)
            self._tarjeta.move(MARGEN_TARJETA, MARGEN_TARJETA)
            _Anclar(self._tarjeta, canvas)

    def refrescar(self) -> None:
        self._espera.start(0)

    def _pintar(self) -> None:
        filas = capas_en_mapa(self._obtener_arbol())
        self.panel.refrescar(filas)
        if self._tarjeta is not None:
            self._tarjeta.refrescar(filas)
            self._tarjeta.raise_()

    def _elegir(self, clave: str) -> None:
        self._arbol.seleccionar(clave)

    def _quitar(self, fila: Fila) -> None:
        if fila[2]:
            quitar_grupo(fila[0])
        else:
            self._quitar_nodo(fila[0])

    def cerrar(self) -> None:
        if self._tarjeta is not None:
            self._tarjeta.deleteLater()
            self._tarjeta = None
