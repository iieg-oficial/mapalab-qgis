from typing import Any, Callable, Optional

from qgis.PyQt.QtCore import QEvent, QObject, QPoint, Qt
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtWidgets import QFrame, QLabel, QWidget

from ..theme import icono_asset, set_role

AYUDA_ASA: str = 'Arrastra para cambiar el orden en el mapa.'

GROSOR_GUIA: int = 2

LADO_ASA: int = 22


def crear_asa() -> QLabel:
    asa = QLabel()
    asa.setPixmap(icono_asset('mover.svg').pixmap(LADO_ASA, LADO_ASA))
    asa.setToolTip(AYUDA_ASA)
    asa.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
    set_role(asa, 'mapa-asa')
    return asa


class Arrastre(QObject):

    def __init__(self, contenedor: QWidget, al_soltar: Callable[[int, int], None],
                 al_desplazar: Optional[Callable[[int], None]] = None) -> None:
        super().__init__(contenedor)
        self._contenedor = contenedor
        self._al_soltar = al_soltar
        self._al_desplazar = al_desplazar
        self._filas: list[QWidget] = []
        self._origen = -1
        self._destino = -1
        self._guia = QFrame(contenedor)
        self._guia.setFixedHeight(GROSOR_GUIA)
        set_role(self._guia, 'mapa-guia')
        self._guia.hide()

    def registrar(self, filas: list[QWidget], asas: list[QWidget]) -> None:
        self._filas = filas
        self._origen = -1
        self._guia.hide()
        for indice, asa in enumerate(asas):
            asa.setProperty('indiceFila', indice)
            asa.installEventFilter(self)

    def _arriba(self, fila: QWidget) -> int:
        return fila.mapTo(self._contenedor, QPoint(0, 0)).y()

    def _indice(self, y: int) -> int:
        for indice, fila in enumerate(self._filas):
            if y < self._arriba(fila) + fila.height() // 2:
                return indice
        return len(self._filas)

    def _pintar_guia(self) -> None:
        if not self._filas:
            return
        if self._destino < len(self._filas):
            fila = self._filas[self._destino]
            y = self._arriba(fila) - GROSOR_GUIA
        else:
            fila = self._filas[-1]
            y = self._arriba(fila) + fila.height()
        x = fila.mapTo(self._contenedor, QPoint(0, 0)).x()
        self._guia.setGeometry(x, max(0, y), fila.width(), GROSOR_GUIA)
        self._guia.show()
        self._guia.raise_()

    def eventFilter(self, objeto: QObject, evento: Any) -> bool:
        tipo = evento.type()
        if tipo == QEvent.Type.MouseButtonPress and evento.button() == Qt.MouseButton.LeftButton:
            self._origen = int(objeto.property('indiceFila'))
            self._destino = self._origen
            objeto.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            return True
        if tipo == QEvent.Type.MouseMove and self._origen >= 0:
            y = self._contenedor.mapFromGlobal(QCursor.pos()).y()
            self._destino = self._indice(y)
            self._pintar_guia()
            if self._al_desplazar is not None:
                self._al_desplazar(y)
            return True
        if tipo == QEvent.Type.MouseButtonRelease and self._origen >= 0:
            origen, destino = self._origen, self._destino
            self._origen = -1
            self._guia.hide()
            objeto.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
            if destino not in (origen, origen + 1):
                self._al_soltar(origen, destino)
            return True
        return False
