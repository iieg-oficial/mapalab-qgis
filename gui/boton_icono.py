from typing import Any, Callable

from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QToolButton, QWidget

from ..theme import set_role
from .sobre_mapa import montar_tarjeta

LADO_BOTON: int = 48

LADO_GLIFO: int = 26


class BotonIcono(QToolButton):

    def __init__(self, icono: QIcon, ayuda: str, al_clic: Callable[[], Any],
                 parent: QWidget) -> None:
        super().__init__(parent)
        self.setIcon(icono)
        self.setIconSize(QSize(LADO_GLIFO, LADO_GLIFO))
        self.setFixedSize(LADO_BOTON, LADO_BOTON)
        self.setToolTip(ayuda)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clicked.connect(al_clic)
        set_role(self, 'mapa-icono')
        montar_tarjeta(self)
        self.hide()
