from typing import Any, Optional

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import (
    QDockWidget,
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
from ..layers.zoom import acercar_a_municipios
from ..model.eventos import temas_de_eventos
from ..model.tree import filter_tree, menu_tree
from ..theme import apply_theme, set_role
from .actions import LayerActions
from .arbol import ArbolCatalogo
from .consulta import ControlConsulta, HerramientaConsulta
from .filtros import ControlFiltros
from .operaciones import Operaciones
from ..tasks import CargarArbolTask, Coordinador
from .icons import boton_de_recarga, olvidar_iconos
from .en_mapa import EnMapa
from .cargando import Cargando
from .filas import acciones_titulo, boton_compartido, fila_servidor
from .lista_mapa import accion
from ..identidad import icono_plugin
from .switch import SwitchModoBase
from .titlebar import Footer, montar_titulo

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
                                       lambda *args: self._al_filtrar(*args),
                                       lambda claves: acercar_a_municipios(
                                           iface.mapCanvas(), self._client.cajas, claves,
                                           self._en_mapa.ocupado()))
        self._ops = Operaciones(iface, self._client, self._tareas, self._actions, self._filtros,
                                self._mensaje, lambda: self._tree, self)
        self._consulta = ControlConsulta(iface, self._crear_consulta)
        self._switch = SwitchModoBase()
        self._switch.setEnabled(False)
        self._switch.cambiado.connect(self._on_cambio_modo)
        self._modo_icono = False
        self._boton_dock: Optional[QWidget] = None
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

        self._reload_button = boton_de_recarga(lambda: self.load_tree(force=True))
        layout.addWidget(self._search)

        self._widget_tree = ArbolCatalogo(
            self._client, self._on_add, self._cerrar_nodo, self._agregar)
        self._widget_tree.itemSelectionChanged.connect(self._actualizar_add)
        self._en_mapa = EnMapa(self._iface, self._widget_tree, lambda: self._tree,
                               self._actions.remove_node, self._filtros, self._switch,
                               self._ops.descargar, lambda: self._client.cajas)
        layout.addWidget(self._widget_tree)
        self._cargando = Cargando(self._widget_tree, icono_plugin(), 'Cargando catálogo…')
        self._boton_dock = self._en_mapa.crear_boton(icono_plugin(), 'Abrir MapaLab',
                                                     self._abrir_desde_icono)
        self.visibilityChanged.connect(self._al_cambiar_visibilidad)

        self._footer = Footer(self._client, FOOTER_BAR_HEIGHT, FOOTER_LOGO_HEIGHT)
        layout.addWidget(self._footer)

        container.setLayout(layout)
        set_role(container, 'panel')
        container.setAutoFillBackground(True)
        self.setWidget(container)

        apply_theme(container)
        self._titulo = montar_titulo(self, self._client, acciones_titulo(
            self._reload_button, boton_compartido(self.abrir_compartido),
            accion('minimizar.svg', 'Minimizar a un icono sobre el mapa',
                   self._reducir_a_icono)))
        self._montar_identidad()

    def _reducir_a_icono(self) -> None:
        self._modo_icono = True
        self.hide()

    def _abrir_desde_icono(self) -> None:
        self.show()
        self.raise_()

    def _al_cambiar_visibilidad(self, visible: bool) -> None:
        if visible:
            self._modo_icono = False
        if self._boton_dock is not None:
            self._boton_dock.setVisible(self._modo_icono and not visible)
        self._en_mapa.acomodar()

    def _montar_identidad(self) -> None:
        self._titulo.refrescar()
        self._footer.refrescar()

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
        self._en_mapa.refrescar()

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
        self._cargando.iniciar()
        tarea = CargarArbolTask(self._client, force)
        self._tareas.lanzar('arbol', tarea, self._arbol_listo, self._arbol_fallo)

    def _arbol_listo(self, arbol: list[dict[str, Any]], desde_cache: bool) -> None:
        self._cargando.detener()
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
        self._cargando.detener()
        self._switch.setEnabled(False)
        self._mensaje(f'No se pudo cargar el catálogo: {detalle}')
        self._url_row.setVisible(True)

    def _menu(self) -> list[dict[str, Any]]:
        return temas_de_eventos(self._client.eventos, self._tree) + menu_tree(self._tree)

    def _aplicar_busqueda(self) -> None:
        if not self._tree:
            return
        texto = self._search.text().strip()
        self._widget_tree.poblar(filter_tree(self._menu(), texto))
        if texto:
            self._widget_tree.expandAll()

    def _actualizar_add(self) -> None:
        node = self._widget_tree.nodo_actual()
        self._filtros.mostrar(node)
        self._en_mapa.abrir(str((node or {}).get('id') or ''))
        if node is not None and node.get('wmsConfig') and self.isVisible():
            self._consulta.activar(forzar=True)

    def _al_filtrar(self, *args: Any) -> None:
        self._ops.al_cambiar(*args)
        self._en_mapa.refrescar()

    def _cerrar_nodo(self, node: dict[str, Any]) -> None:
        if es_grupo(node):
            quitar_grupo(str(node.get('id') or ''))
        else:
            self._actions.remove_node(str(node.get('id') or ''))

    def _mensaje(self, texto: str) -> None:
        self._en_mapa.avisar(texto)

    def _reportar(self, resultado: tuple[bool, str]) -> None:
        self._mensaje(resultado[1])

    def _agregar(self, node: dict[str, Any], completa: bool = False,
                 descargar: bool = False) -> None:
        self._ops.agregar(node, completa, descargar)

    def abrir_compartido(self) -> None:
        self._ops.abrir_compartido()

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

    def cerrar(self) -> None:
        self._consulta.desactivar()
        self._en_mapa.cerrar()
        self._desconectar_proyecto()
        self._tareas.cancelar_todo()
