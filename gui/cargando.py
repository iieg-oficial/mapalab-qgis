from typing import Any

from qgis.PyQt.QtCore import QEvent, QObject, QRect, QRectF, Qt, QTimer
from qgis.PyQt.QtGui import QColor, QIcon, QPainter, QPen
from qgis.PyQt.QtWidgets import QWidget

from ..theme import color_de_rol

LADO_ICONO: int = 34

RADIO: int = 32

GROSOR: int = 3

PASO_GRADOS: int = 14

PERIODO_MS: int = 40

ARCO_GRADOS: int = 100

OPACIDAD: int = 238


class Cargando(QWidget):

    def __init__(self, base: QWidget, icono: QIcon, texto: str) -> None:
        super().__init__(base)
        self._base = base
        self._texto = texto
        self._angulo = 0
        self._icono = icono.pixmap(LADO_ICONO, LADO_ICONO)
        self._tinta = QColor(color_de_rol('search', 'color', '#5C2472'))
        self._gris = QColor(color_de_rol('quiet', 'color', '#465055'))
        self._fondo = QColor(color_de_rol('panel', 'background-color', '#FFFFFF'))
        self._fondo.setAlpha(OPACIDAD)
        self._reloj = QTimer(self)
        self._reloj.setInterval(PERIODO_MS)
        self._reloj.timeout.connect(self._girar)
        base.installEventFilter(self)
        self.hide()

    def iniciar(self) -> None:
        self.setGeometry(self._base.rect())
        self.show()
        self.raise_()
        self._reloj.start()

    def detener(self) -> None:
        self._reloj.stop()
        self.hide()

    def eventFilter(self, objeto: QObject, evento: Any) -> bool:
        if evento.type() == QEvent.Type.Resize and self.isVisible():
            self.setGeometry(self._base.rect())
        return False

    def _girar(self) -> None:
        self._angulo = (self._angulo + PASO_GRADOS) % 360
        self.update()

    def paintEvent(self, evento: Any) -> None:
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        pintor.fillRect(self.rect(), self._fondo)
        cx = self.width() // 2
        cy = self.height() // 2 - RADIO
        pintor.setPen(QPen(self._tinta, GROSOR, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        pintor.drawArc(QRectF(cx - RADIO, cy - RADIO, 2 * RADIO, 2 * RADIO),
                       -self._angulo * 16, ARCO_GRADOS * 16)
        pintor.drawPixmap(cx - LADO_ICONO // 2, cy - LADO_ICONO // 2, self._icono)
        pintor.setPen(self._gris)
        pintor.drawText(QRect(0, cy + RADIO + 12, self.width(), 24),
                        int(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop),
                        self._texto)
