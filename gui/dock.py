from typing import Any, Optional

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ..api.client import MapaLabClient
from ..config import (
    FOOTER_BAR_HEIGHT,
    FOOTER_LOGO_HEIGHT,
    SECTION_GAP,
    get_base_url,
    set_base_url,
)
from ..layers.grupos import es_grupo, quitar_grupo
from ..layers.limites import modo_actual
from ..model.tree import filter_tree
from ..theme import apply_theme, set_role
from .actions import LayerActions
from .arbol import ArbolCatalogo
from .consulta import ControlConsulta, HerramientaConsulta
from .filtros import ControlFiltros
from .operaciones import Operaciones
from ..tasks import CargarArbolTask, Coordinador
from .icons import boton_de_recarga, icono_de_recarga, olvidar_iconos
from .filas import fila_acciones, fila_limpieza, fila_servidor
from .switch import SwitchModoBase
from .titlebar import Footer, montar_titulo

TEXTO_CAPA: str = 'Agregar al mapa'

TEXTO_GRUPO: str = 'Agregar grupo completo'

ESPERA_BUSQUEDA_MS: int = 200

ESQUEMAS: tuple[str, ...] = ('https://', 'http://')


class MapaLabDock(QDockWidget):

    def __init__(self, iface: Any, parent: Optional[QWidget] = None) -> None:
        super().__init__('MapaLab', parent)
        self.setObjectName('MapaLabDock')
        self._iface = iface
        set_role(self, 'panel')
        self.setAutoFillBackground(True)
        self._client = MapaLabClient()
        self._tareas = Coordinador()
        self._actions = LayerActions(iface, self._client, self._tareas)
        self._tree: list[dict[str, Any]] = []
        self._filtros = ControlFiltros(self._client, self._tareas,
                                       lambda *args: self._ops.al_cambiar(*args))
        self._ops = Operaciones(iface, self._client, self._tareas, self._actions, self._filtros,
                                self._mensaje, lambda: self._tree, self)
        self._consulta = ControlConsulta(iface, self._crear_consulta)
        self._switch = SwitchModoBase()
        self._switch.setEnabled(False)
        self._switch.cambiado.connect(self._on_cambio_modo)
        self._espera = QTimer(self)
        self._espera.setSingleShot(True)
        self._espera.setInterval(ESPERA_BUSQUEDA_MS)
        self._espera.timeout.connect(self._aplicar_busqueda)
        self._build_ui()
        apply_theme(self)
        self._conectar_proyecto()
        self._refresh_url_state()

    def _build_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(SECTION_GAP)

        self._url_row, self._url_input = fila_servidor(self._on_save_url)
        layout.addWidget(self._url_row)

        self._search = QLineEdit()
        self._search.setPlaceholderText('Buscar capa…')
        self._search.textChanged.connect(lambda _: self._espera.start())
        set_role(self._search, 'search')

        search_row = QHBoxLayout()
        search_row.setContentsMargins(0, 0, 0, 0)
        search_row.setSpacing(8)
        self._reload_button = boton_de_recarga(
            self._client, lambda: self.load_tree(force=True))
        search_row.addWidget(self._search)
        search_row.addWidget(self._reload_button)
        layout.addLayout(search_row)

        self._widget_tree = ArbolCatalogo(
            self._client, self._on_add, self._alternar_grupo, self._cerrar_nodo,
            self._agregar)
        self._widget_tree.itemSelectionChanged.connect(self._actualizar_add)
        layout.addWidget(self._widget_tree)
        layout.addWidget(self._filtros.widget)

        buttons, self._add_button, self._download_button = fila_acciones(
            self._on_add, self._on_download, TEXTO_CAPA)
        layout.addLayout(buttons)
        layout.addLayout(fila_limpieza(self._on_clear_seleccion, self.abrir_compartido))

        self._status = QLabel('')
        self._status.setWordWrap(True)
        self._status.setVisible(False)
        layout.addWidget(self._status)

        self._footer = Footer(self._client, FOOTER_BAR_HEIGHT, FOOTER_LOGO_HEIGHT)
        layout.addWidget(self._footer)

        container.setLayout(layout)
        set_role(container, 'panel')
        container.setAutoFillBackground(True)
        self.setWidget(container)

        apply_theme(container)
        self._titulo = montar_titulo(self, self._client, self._switch)
        self._montar_identidad()

    def _montar_identidad(self) -> None:
        self._titulo.refrescar()
        self._footer.refrescar()
        self._reload_button.setIcon(icono_de_recarga(self._client))

    def _crear_consulta(self, canvas: Any) -> HerramientaConsulta:
        return HerramientaConsulta(canvas, self._client, self._tareas,
                                   self._widget_tree.nodo_actual, self._al_consultar,
                                   self._filtros.parametros_de)

    def _conectar_proyecto(self) -> None:
        proyecto = QgsProject.instance()
        proyecto.layersAdded.connect(self._sincronizar_switch)
        proyecto.layersRemoved.connect(self._sincronizar_switch)
        self._sincronizar_switch()

    def _desconectar_proyecto(self) -> None:
        proyecto = QgsProject.instance()
        for senal in (proyecto.layersAdded, proyecto.layersRemoved):
            try:
                senal.disconnect(self._sincronizar_switch)
            except TypeError:
                pass

    def _sincronizar_switch(self, *args: Any) -> None:
        self._switch.mostrar(modo_actual())
        self._widget_tree.sincronizar()

    def _on_cambio_modo(self, modo: str) -> None:
        if not self._tree:
            self._mensaje('El catálogo aún no carga.')
            self._sincronizar_switch()
            return
        self._reportar(self._actions.set_base_mode(self._tree, modo))
        self._sincronizar_switch()

    def _refresh_url_state(self) -> None:
        base_url = get_base_url()
        self._url_input.setText(base_url)
        configured = bool(base_url)
        self._url_row.setVisible(not configured)
        if configured:
            self.load_tree()
        else:
            self._mensaje('Configura la dirección del servidor para cargar el catálogo.')

    def mostrar_servidor(self) -> None:
        self._url_input.setText(get_base_url())
        self._url_row.setVisible(True)
        self._url_input.setFocus()

    def _on_save_url(self) -> None:
        value = self._url_input.text().strip().rstrip('/')
        if not value.lower().startswith(ESQUEMAS):
            self._mensaje('La dirección empieza con https:// (o http:// en un servidor interno).')
            return
        if value == get_base_url():
            self._refresh_url_state()
            return
        self._tareas.cancelar('arbol')
        self._client.olvidar()
        self._filtros.olvidar()
        olvidar_iconos()
        self._tree = []
        self._widget_tree.poblar([])
        set_base_url(value)
        self._url_row.setVisible(False)
        self.load_tree(force=True)

    def load_tree(self, force: bool = False) -> None:
        if self._tareas.ocupado('arbol'):
            return
        self._mensaje('Cargando catálogo…')
        tarea = CargarArbolTask(self._client, force)
        self._tareas.lanzar('arbol', tarea, self._arbol_listo, self._arbol_fallo)

    def _arbol_listo(self, arbol: list[dict[str, Any]], desde_cache: bool) -> None:
        self._tree = arbol
        olvidar_iconos()
        self._filtros.cargar_municipios()
        self._montar_identidad()
        self._aplicar_busqueda()
        self._switch.setEnabled(True)
        self._sincronizar_switch()
        self._mensaje('Sin conexión con el servidor: se muestra el último catálogo guardado.'
                      if desde_cache else '')

    def _arbol_fallo(self, detalle: str) -> None:
        self._switch.setEnabled(False)
        self._mensaje(f'No se pudo cargar el catálogo: {detalle}')
        self._url_row.setVisible(True)

    def _aplicar_busqueda(self) -> None:
        if not self._tree:
            return
        texto = self._search.text().strip()
        self._widget_tree.poblar(filter_tree(self._tree, texto))
        if texto:
            self._widget_tree.expandAll()

    def _actualizar_add(self) -> None:
        node = self._widget_tree.nodo_actual()
        self._add_button.setText(TEXTO_GRUPO if es_grupo(node) else TEXTO_CAPA)
        self._filtros.mostrar(node)
        if node is not None and node.get('wmsConfig') and self.isVisible():
            self._consulta.activar(forzar=True)

    def _cerrar_nodo(self, node: dict[str, Any]) -> None:
        self._actions.remove_node(str(node.get('id') or ''))

    def _alternar_grupo(self, node: dict[str, Any], marcado: bool) -> None:
        if marcado:
            self._agregar(node)
        else:
            quitar_grupo(str(node.get('id') or ''))

    def _mensaje(self, texto: str) -> None:
        self._status.setText(texto)
        self._status.setVisible(bool(texto))

    def _reportar(self, resultado: tuple[bool, str]) -> None:
        self._mensaje(resultado[1])

    def _agregar(self, node: dict[str, Any], completa: bool = False,
                 descargar: bool = False) -> None:
        self._ops.agregar(node, completa, descargar)

    def abrir_compartido(self) -> None:
        self._ops.abrir_compartido()

    def _on_clear_seleccion(self) -> None:
        quitadas = self._actions.clear_selections()
        self._mensaje('' if quitadas else 'No hay capas de selección en el proyecto.')

    def _on_add(self) -> None:
        node = self._widget_tree.nodo_para_accion(permitir_grupo=True)
        if node is not None:
            self._agregar(node)

    def _al_consultar(self, datos: Optional[tuple], aviso: str) -> None:
        if datos is None:
            self._mensaje(aviso)
            return
        self._reportar(self._actions.abrir_feature(datos))

    def showEvent(self, evento: Any) -> None:
        super().showEvent(evento)
        self._consulta.activar()

    def hideEvent(self, evento: Any) -> None:
        super().hideEvent(evento)
        self._consulta.desactivar()

    def _on_download(self) -> None:
        node = self._widget_tree.nodo_para_accion()
        if node is not None:
            self._ops.descargar(node)

    def cerrar(self) -> None:
        self._consulta.desactivar()
        self._desconectar_proyecto()
        self._tareas.cancelar_todo()
