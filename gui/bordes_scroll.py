from typing import Any, Callable

from qgis.PyQt.QtCore import QEvent, QObject, QSize, Qt
from qgis.PyQt.QtGui import QColor, QIcon, QLinearGradient, QPainter, QTransform
from qgis.PyQt.QtWidgets import QAbstractScrollArea, QToolButton, QWidget

from ..theme import icono_asset, set_role

ALTO_BORDE: int = 32

LADO_FLECHA: int = 22

MARGEN_FLECHA: int = 4

AYUDAS: dict[bool, str] = {True: 'Ir al inicio', False: 'Ir al final'}


class _Desvanecido(QWidget):

    def __init__(self, area: QWidget, arriba: bool, color: str) -> None:
        super().__init__(area)
        self._arriba = arriba
        self._color = QColor(color)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def paintEvent(self, evento: Any) -> None:
        gradiente = QLinearGradient(0, 0 if self._arriba else self.height(),
                                    0, self.height() if self._arriba else 0)
        transparente = QColor(self._color)
        transparente.setAlpha(0)
        gradiente.setColorAt(0, self._color)
        gradiente.setColorAt(1, transparente)
        pintor = QPainter(self)
        pintor.fillRect(self.rect(), gradiente)


def _flecha(arriba: bool) -> QIcon:
    icono = icono_asset('flecha.svg')
    if not arriba:
        return icono
    giro = icono.pixmap(LADO_FLECHA, LADO_FLECHA).transformed(QTransform().rotate(180))
    return QIcon(giro)


def _boton(area: QWidget, arriba: bool, al_clic: Callable[[], Any]) -> QToolButton:
    boton = QToolButton(area)
    boton.setIcon(_flecha(arriba))
    boton.setIconSize(QSize(12, 12))
    boton.setFixedSize(LADO_FLECHA, LADO_FLECHA)
    boton.setAutoRaise(True)
    boton.setToolTip(AYUDAS[arriba])
    boton.setCursor(Qt.CursorShape.PointingHandCursor)
    boton.clicked.connect(al_clic)
    set_role(boton, 'borde-scroll')
    return boton


class BordesScroll(QObject):

    def __init__(self, area: QAbstractScrollArea, color: str = '#FFFFFF') -> None:
        super().__init__(area)
        self._area = area
        barra = area.verticalScrollBar()
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._bordes = {arriba: _Desvanecido(area, arriba, color) for arriba in (True, False)}
        self._flechas = {
            True: _boton(area, True, lambda: barra.setValue(barra.minimum())),
            False: _boton(area, False, lambda: barra.setValue(barra.maximum())),
        }
        barra.valueChanged.connect(self._actualizar)
        barra.rangeChanged.connect(self._actualizar)
        area.installEventFilter(self)
        self._actualizar()

    def eventFilter(self, objeto: QObject, evento: Any) -> bool:
        if evento.type() in (QEvent.Type.Resize, QEvent.Type.Show):
            self._actualizar()
        return False

    def _actualizar(self, *args: Any) -> None:
        barra = self._area.verticalScrollBar()
        vista = self._area.viewport().geometry()
        visibles = {True: barra.value() > barra.minimum(),
                    False: barra.value() < barra.maximum()}
        for arriba, borde in self._bordes.items():
            y = vista.top() if arriba else vista.bottom() - ALTO_BORDE + 1
            borde.setGeometry(vista.left(), y, vista.width(), ALTO_BORDE)
            borde.setVisible(visibles[arriba])
            borde.raise_()
            flecha = self._flechas[arriba]
            fy = (vista.top() + MARGEN_FLECHA if arriba
                  else vista.bottom() - LADO_FLECHA - MARGEN_FLECHA + 1)
            flecha.move(vista.center().x() - LADO_FLECHA // 2, fy)
            flecha.setVisible(visibles[arriba])
            flecha.raise_()
