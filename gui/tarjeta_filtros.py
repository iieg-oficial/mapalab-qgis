from typing import Any, Callable

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtWidgets import QHBoxLayout, QWidget

from ..theme import icono_asset, set_role
from .boton_icono import BotonIcono
from .lista_mapa import ANCHO_TARJETA, AYUDA_MINIMIZAR, accion

MARGEN: int = 8


class TarjetaFiltros(QWidget):

    def __init__(self, municipio: QWidget, al_ajustar: Callable[[], Any],
                 parent: QWidget) -> None:
        super().__init__(parent)
        self._municipio = municipio
        self._al_ajustar = al_ajustar
        self._icono = False
        self.boton = BotonIcono(icono_asset('filtro.svg'), 'Filtro de municipio: clic para abrir',
                                self._alternar_icono, parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(MARGEN, MARGEN, MARGEN, MARGEN)
        layout.addWidget(municipio, 1)
        layout.addWidget(accion('minimizar.svg', AYUDA_MINIMIZAR, self._alternar_icono), 0,
                         Qt.AlignmentFlag.AlignVCenter)
        set_role(self, 'mapa-tarjeta')
        self.hide()

    def _alternar_icono(self) -> None:
        self._icono = not self._icono
        self.refrescar()

    def refrescar(self) -> None:
        QTimer.singleShot(0, self._ajustar)

    def _ajustar(self) -> None:
        con_municipio = any(not hijo.isHidden() for hijo in self._municipio.findChildren(QWidget)
                            if hijo.parentWidget() is self._municipio)
        self._municipio.setVisible(con_municipio)
        self.setVisible(con_municipio and not self._icono)
        self.boton.setVisible(con_municipio and self._icono)
        if con_municipio:
            self.setFixedWidth(ANCHO_TARJETA)
            self.setFixedHeight(self.sizeHint().height())
        self._al_ajustar()
