from typing import Any, Callable, Optional

from qgis.PyQt.QtWidgets import QWidget

from ..api.client import MapaLabClient
from ..layers.filtros import Filtro
from ..layers.grupos import capas_de_grupo, es_grupo, quitar_grupo
from ..tasks import Coordinador
from .actions import LayerActions
from .compartido import DialogoCompartido
from .filtros import ControlFiltros

CLAVE_DESCARGA: str = 'descarga'


class Operaciones:

    def __init__(self, iface: Any, client: MapaLabClient, tareas: Coordinador,
                 actions: LayerActions, filtros: ControlFiltros,
                 mensaje: Callable[[str], None],
                 arbol: Callable[[], list[dict[str, Any]]],
                 parent: Optional[QWidget] = None) -> None:
        self._iface = iface
        self._client = client
        self._tareas = tareas
        self._actions = actions
        self._filtros = filtros
        self._mensaje = mensaje
        self._arbol = arbol
        self._parent = parent

    def agregar(self, node: dict[str, Any], completa: bool = False,
                descargar: bool = False) -> None:
        if descargar:
            self.descargar(node, completa)
            return

        def con_filtro(filtro: Filtro, columna: Optional[str]) -> None:
            self._mensaje(self._actions.add_as_wms(node, completa, filtro, columna)[1])

        self._filtros.con_filtro(node, con_filtro)

    def descargar(self, node: dict[str, Any], completa: bool = False) -> None:
        if self._tareas.ocupado(CLAVE_DESCARGA):
            self._mensaje('Ya hay una descarga en curso.')
            return

        def con_filtro(filtro: Filtro, columna: Optional[str]) -> None:
            tarea, error = self._actions.download_as_vector(
                node, self._parent, completa, filtro, columna)
            if tarea is None:
                self._mensaje(error)
                return
            self._mensaje('Descargando… puedes seguir trabajando, aunque cierres el panel.')
            self._tareas.lanzar(CLAVE_DESCARGA, tarea,
                                lambda path: self._mensaje(f'Guardado en {path}'),
                                self._mensaje)

        self._filtros.con_filtro(node, con_filtro)

    def al_cambiar(self, node: dict[str, Any], filtro: Filtro, columna: Optional[str]) -> None:
        if es_grupo(node):
            node_id = str(node.get('id') or '')
            if capas_de_grupo(node_id):
                quitar_grupo(node_id)
                self._mensaje(self._actions.add_group(node, False, filtro)[1])
            return
        self._mensaje(self._actions.aplicar_filtro(node, filtro, columna)[1])

    def abrir_compartido(self) -> None:
        canvas = self._iface.mapCanvas() if self._iface is not None else None
        dialogo = DialogoCompartido(self._client, self._tareas, self._arbol, canvas,
                                    self._mensaje, self._parent)
        dialogo.exec_()
