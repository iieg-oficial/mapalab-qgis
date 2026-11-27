from typing import Any

from qgis.PyQt.QtCore import QEvent, QObject, Qt, QTimer
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..theme import apply_theme, icono_asset, set_role, sombra

MARGEN: int = 12

SEPARACION: int = MARGEN

MARGEN_AVISO: int = MARGEN

ANCHO_MAXIMO_AVISO: int = 460

LADO_ICONO: int = 26

DURACION_AVISO_MS: int = 6000


SOMBRA_BLUR: float = 20.0

SOMBRA_Y: float = 5.0

SOMBRA: tuple[int, int, int, int] = (26, 38, 100, 34)


def montar_tarjeta(tarjeta: QWidget) -> None:
    apply_theme(tarjeta)
    sombra(tarjeta, SOMBRA_BLUR, SOMBRA_Y, QColor(*SOMBRA)).setEnabled(True)


class Apilado(QObject):

    def __init__(self, canvas: QWidget) -> None:
        super().__init__(canvas)
        self._canvas = canvas
        self._tarjetas: list[QWidget] = []
        canvas.installEventFilter(self)

    def agregar(self, tarjeta: QWidget, primero: bool = False) -> None:
        self._tarjetas.insert(0 if primero else len(self._tarjetas), tarjeta)
        self.acomodar()

    def eventFilter(self, objeto: QObject, evento: Any) -> bool:
        if evento.type() == QEvent.Type.Resize:
            self.acomodar()
        return False

    def acomodar(self) -> None:
        y = MARGEN
        for tarjeta in self._tarjetas:
            if tarjeta.isHidden():
                continue
            tarjeta.move(max(0, self._canvas.width() - tarjeta.width() - MARGEN), y)
            tarjeta.raise_()
            y += tarjeta.height() + SEPARACION


class AvisoMapa(QWidget):

    def __init__(self, canvas: QWidget) -> None:
        super().__init__(canvas)
        self._canvas = canvas
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 16, 8)
        layout.setSpacing(10)
        icono = QLabel()
        icono.setPixmap(icono_asset('info.svg').pixmap(LADO_ICONO, LADO_ICONO))
        self._texto = QLabel('')
        self._texto.setWordWrap(True)
        set_role(self._texto, 'mapa-aviso-texto')
        layout.addWidget(icono, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._texto, 1)
        set_role(self, 'mapa-aviso')
        montar_tarjeta(self)
        self.setToolTip('Clic para cerrar')
        self._reloj = QTimer(self)
        self._reloj.setSingleShot(True)
        self._reloj.timeout.connect(self.hide)
        canvas.installEventFilter(self)
        self.hide()

    def mostrar(self, texto: str) -> None:
        if not texto:
            self.hide()
            return
        self._texto.setText(texto)
        ancho = self._texto.fontMetrics().horizontalAdvance(texto) + 4
        self._texto.setFixedWidth(min(ancho, ANCHO_MAXIMO_AVISO))
        self.adjustSize()
        self._colocar()
        self.show()
        self.raise_()
        self._reloj.start(DURACION_AVISO_MS)

    def _colocar(self) -> None:
        x = (self._canvas.width() - self.width()) // 2
        self.move(max(0, x), max(0, self._canvas.height() - self.height() - MARGEN_AVISO))

    def mousePressEvent(self, evento: Any) -> None:
        self.hide()

    def eventFilter(self, objeto: QObject, evento: Any) -> bool:
        if evento.type() == QEvent.Type.Resize and self.isVisible():
            self._colocar()
        return False
