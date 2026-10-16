from typing import Any, Optional

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..api.client import MapaLabClient
from ..assets_cache import fetch_asset
from ..config import LOGO_HEIGHT
from ..identidad import logo_urls
from ..theme import set_role

TITULO: str = 'MapaLab'


def es_tema_oscuro(widget: QWidget) -> bool:
    return widget.palette().window().color().lightness() < 128


def _widget_svg(datos: bytes, alto: int = LOGO_HEIGHT) -> Optional[QWidget]:
    try:
        from qgis.PyQt.QtSvg import QSvgWidget
    except ImportError:
        try:
            from qgis.PyQt.QtSvgWidgets import QSvgWidget
        except ImportError:
            return None

    widget = QSvgWidget()
    widget.load(datos)
    tamano = widget.renderer().defaultSize()
    if not tamano.isValid() or tamano.height() <= 0:
        return None
    ancho = int(tamano.width() * alto / tamano.height())
    widget.setFixedSize(ancho, alto)
    return widget


FOOTER_HEIGHT: int = 26


def logo_widget(client: MapaLabClient, marca: str, oscuro: bool,
                alto: int = FOOTER_HEIGHT) -> Optional[QWidget]:
    datos = fetch_asset(client, logo_urls(marca, oscuro), solo_cache=True)
    if not datos:
        return None
    widget = _widget_svg(datos, alto)
    if widget is not None:
        widget.setToolTip(marca.upper())
    return widget


def _vaciar(layout: QHBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def montar_footer(footer: QWidget, layout: QHBoxLayout, client: MapaLabClient,
                  alto: int) -> None:
    _vaciar(layout)
    oscuro = es_tema_oscuro(footer)
    iieg = logo_widget(client, 'iieg', oscuro, alto)
    jalisco = logo_widget(client, 'jalisco', oscuro, alto)

    footer.setVisible(iieg is not None or jalisco is not None)
    if iieg is not None:
        layout.addWidget(iieg, 0, Qt.AlignmentFlag.AlignVCenter)
    layout.addStretch(1)
    if jalisco is not None:
        layout.addWidget(jalisco, 0, Qt.AlignmentFlag.AlignVCenter)


class Footer(QWidget):

    def __init__(self, client: MapaLabClient, alto_barra: int, alto_logo: int,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._client = client
        self._alto_logo = alto_logo
        self.setFixedHeight(alto_barra)
        self._layout = QHBoxLayout()
        self._layout.setContentsMargins(10, 6, 10, 6)
        self.setLayout(self._layout)

    def refrescar(self) -> None:
        montar_footer(self, self._layout, self._client, self._alto_logo)


def montar_titulo(dock: Any, client: MapaLabClient, switch: QWidget) -> 'TitleBar':
    from ..theme import apply_theme

    barra = TitleBar(client, switch, dock)
    set_role(barra, 'panel')
    barra.setAutoFillBackground(True)
    apply_theme(barra)
    barra.cargar()
    dock.setTitleBarWidget(barra)
    return barra


class TitleBar(QWidget):

    def __init__(self, client: MapaLabClient, switch: Optional[QWidget] = None,
                 parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._client = client
        self._switch = switch
        self.setMinimumHeight(LOGO_HEIGHT + 12)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)
        self.setLayout(layout)
        self._layout = layout
        self._marca: Optional[QWidget] = None

    def cargar(self) -> None:
        self._marca = self._logo_o_texto('mapalab', es_tema_oscuro(self), TITULO)
        self._layout.addWidget(self._marca)
        self._layout.addStretch(1)

        if self._switch is not None:
            self._layout.addWidget(self._switch, 0, Qt.AlignmentFlag.AlignVCenter)

    def refrescar(self) -> None:
        if self._marca is None or not isinstance(self._marca, QLabel):
            return
        logo = self._logo('mapalab', es_tema_oscuro(self))
        if logo is None:
            return
        self._layout.replaceWidget(self._marca, logo)
        self._marca.deleteLater()
        self._marca = logo

    def _logo(self, marca: str, oscuro: bool) -> Optional[QWidget]:
        return logo_widget(self._client, marca, oscuro, LOGO_HEIGHT)

    def _logo_o_texto(self, marca: str, oscuro: bool, texto: str) -> QWidget:
        widget = self._logo(marca, oscuro)
        if widget is not None:
            return widget
        etiqueta = QLabel(texto)
        set_role(etiqueta, 'title')
        return etiqueta
