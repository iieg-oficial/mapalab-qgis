from typing import Any, Callable

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QHBoxLayout, QWidget

from ..theme import set_role
from .lista_mapa import ANCHO_TARJETA

MARGEN: int = 8

ALTO_COMPACTO: int = 68


class TarjetaFiltros(QWidget):

    def __init__(self, municipio: QWidget, al_ajustar: Callable[[], Any],
                 parent: QWidget) -> None:
        super().__init__(parent)
        self._municipio = municipio
        self._al_ajustar = al_ajustar
        self.alto_compacto = ALTO_COMPACTO
        layout = QHBoxLayout(self)
        layout.setContentsMargins(MARGEN, MARGEN, MARGEN, MARGEN)
        layout.addWidget(municipio, 1)
        set_role(self, 'mapa-tarjeta')
        self.hide()

    def refrescar(self) -> None:
        QTimer.singleShot(0, self._ajustar)

    def _ajustar(self) -> None:
        con_municipio = any(not hijo.isHidden() for hijo in self._municipio.findChildren(QWidget)
                            if hijo.parentWidget() is self._municipio)
        self._municipio.setVisible(con_municipio)
        self.setVisible(con_municipio)
        if con_municipio:
            self.setFixedWidth(ANCHO_TARJETA)
            self.setFixedHeight(self.sizeHint().height())
            self.alto_compacto = self.height()
        self._al_ajustar()
