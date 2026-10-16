from typing import Any, Callable, Iterator, Optional

from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsApplication, QgsFeedback, QgsProject, QgsTask

from .api.client import MapaLabCancelado, MapaLabClient, MapaLabError
from .assets_cache import fetch_asset
from .config import LOGOS
from .identidad import guardar_icono, icono_urls, logo_urls, refrescar_urls, tema_icono_urls
from .layers.metadata import apply_metadata
from .layers.vector import add_vector_layer, download_vector
from .model.tree import alias_de_tema, clean_label, hydrate_tree, workspace_and_layer

PESO_CATALOGO: float = 40.0


class _TareaMapaLab(QgsTask):

    def __init__(self, descripcion: str, flags: Any = QgsTask.Flag.CanCancel) -> None:
        super().__init__(descripcion, flags)
        self._feedback = QgsFeedback()
        self._error: str = ''

    def cancel(self) -> None:
        self._feedback.cancel()
        super().cancel()


def _urls_de_nodos(nodos: list[dict[str, Any]]) -> Iterator[list[str]]:
    for nodo in nodos:
        url = nodo.get('iconUrl')
        if isinstance(url, str) and url:
            yield [url]
        yield from _urls_de_nodos(nodo.get('children') or [])


class CargarArbolTask(_TareaMapaLab):

    listo = pyqtSignal(list, bool)
    fallo = pyqtSignal(str)

    def __init__(self, client: MapaLabClient, force: bool = False) -> None:
        super().__init__('MapaLab: catálogo de capas')
        self._client = client
        self._force = force
        self._arbol: list[dict[str, Any]] = []
        self._desde_cache = False

    def run(self) -> bool:
        try:
            crudo = self._client.fetch_tree(force=self._force, feedback=self._feedback)
        except MapaLabCancelado:
            return False
        except MapaLabError as exc:
            self._error = str(exc)
            return False

        self._desde_cache = self._client.desde_cache
        self.setProgress(PESO_CATALOGO)
        self._arbol = hydrate_tree(crudo)
        if not self._desde_cache:
            self._cargar_municipios()
            self._precargar()
        return not self.isCanceled()

    def _cargar_municipios(self) -> None:
        try:
            self._client.municipios = self._client.fetch_municipios(feedback=self._feedback)
        except MapaLabError:
            self._client.municipios = []

    def _pendientes(self) -> list[list[str]]:
        listas: list[list[str]] = [icono_urls(), refrescar_urls()]
        for marca in LOGOS:
            listas.extend([logo_urls(marca, False), logo_urls(marca, True)])
        for nodo in self._arbol:
            alias = alias_de_tema(nodo)
            if alias:
                listas.extend([tema_icono_urls(alias), tema_icono_urls(alias, True)])
        listas.extend(_urls_de_nodos(self._arbol))
        return listas

    def _precargar(self) -> None:
        pendientes = self._pendientes()
        total = len(pendientes) or 1
        for indice, urls in enumerate(pendientes):
            if self.isCanceled():
                return
            try:
                datos = fetch_asset(self._client, urls, self._feedback)
            except MapaLabCancelado:
                return
            if indice == 0 and datos:
                guardar_icono(datos)
            self.setProgress(PESO_CATALOGO + (100.0 - PESO_CATALOGO) * (indice + 1) / total)

    def finished(self, result: bool) -> None:
        if self.isCanceled():
            return
        if result:
            self.listo.emit(self._arbol, self._desde_cache)
        else:
            self.fallo.emit(self._error or 'El servidor no respondió.')


class DescargarVectorTask(_TareaMapaLab):

    listo = pyqtSignal(str)
    fallo = pyqtSignal(str)

    def __init__(self, client: MapaLabClient, node: dict[str, Any], target_dir: str,
                 aplicar_filtro: bool = True, extra_cql: str = '', sufijo: str = '') -> None:
        etiqueta = clean_label(node.get('label') or 'capa')
        super().__init__(f'MapaLab: descargando «{etiqueta}»')
        self._client = client
        self._node = node
        self._target_dir = target_dir
        self._aplicar_filtro = aplicar_filtro
        self._extra_cql = extra_cql
        self._sufijo = sufijo
        self._etiqueta = etiqueta
        self._path: Optional[str] = None
        self._metadata: Any = None

    def _progreso(self, recibido: int, total: int) -> None:
        if total > 0:
            self.setProgress(min(99.0, recibido * 100.0 / total))

    def _metadata_remota(self) -> Any:
        workspace, layer = workspace_and_layer(self._node)
        if not workspace or not layer:
            return None
        try:
            return self._client.fetch_metadata(workspace, layer, feedback=self._feedback)
        except MapaLabError:
            return None

    def run(self) -> bool:
        path, error = download_vector(
            self._node, self._client, self._target_dir,
            apply_node_filter=self._aplicar_filtro, extra_cql=self._extra_cql,
            sufijo=self._sufijo, feedback=self._feedback, on_progress=self._progreso)

        if self.isCanceled():
            return False
        if path is None:
            self._error = f'No se pudo descargar «{self._etiqueta}»: {error}'
            return False

        self._path = path
        self._metadata = self._metadata_remota()
        self.setProgress(100.0)
        return True

    def finished(self, result: bool) -> None:
        if not result or self._path is None:
            if self.isCanceled():
                self.fallo.emit(f'Se canceló la descarga de «{self._etiqueta}».')
            else:
                self.fallo.emit(self._error or f'No se pudo descargar «{self._etiqueta}».')
            return

        capa = add_vector_layer(self._path, self._node)
        if capa is None:
            self.fallo.emit(f'Se descargó en {self._path}, pero QGIS no pudo abrirlo.')
            return

        if self._metadata is not None:
            apply_metadata(capa, self._metadata, self._node)
        self.listo.emit(self._path)


class MetadataTask(_TareaMapaLab):

    listo = pyqtSignal(str)
    fallo = pyqtSignal(str)

    def __init__(self, client: MapaLabClient, node: dict[str, Any], layer_id: str) -> None:
        super().__init__('MapaLab: metadata', QgsTask.Flag.CanCancel | QgsTask.Flag.Silent)
        self._client = client
        self._node = node
        self._layer_id = layer_id
        self._payload: Any = None

    def run(self) -> bool:
        workspace, layer = workspace_and_layer(self._node)
        if not workspace or not layer:
            return False
        try:
            self._payload = self._client.fetch_metadata(workspace, layer, feedback=self._feedback)
        except MapaLabError:
            return False
        return True

    def finished(self, result: bool) -> None:
        capa = QgsProject.instance().mapLayer(self._layer_id)
        if result and capa is not None:
            apply_metadata(capa, self._payload, self._node)
        self.listo.emit(self._layer_id)


class ConsultaTask(_TareaMapaLab):

    listo = pyqtSignal(str)
    fallo = pyqtSignal(str)

    def __init__(self, client: MapaLabClient, url: str) -> None:
        super().__init__('MapaLab: consulta', QgsTask.Flag.CanCancel | QgsTask.Flag.Silent)
        self._client = client
        self._url = url
        self._texto = ''

    def run(self) -> bool:
        try:
            self._texto = self._client.fetch_text(self._url, feedback=self._feedback)
        except MapaLabCancelado:
            return False
        except MapaLabError as exc:
            self._error = str(exc)
            return False
        return True

    def finished(self, result: bool) -> None:
        if result:
            self.listo.emit(self._texto)
        elif not self.isCanceled():
            self.fallo.emit(f'No se pudo consultar la capa: {self._error}')


class PeriodicidadTask(_TareaMapaLab):

    listo = pyqtSignal(dict, str)
    fallo = pyqtSignal(str)

    def __init__(self, client: MapaLabClient, node: dict[str, Any]) -> None:
        super().__init__('MapaLab: fechas de la capa', QgsTask.Flag.CanCancel | QgsTask.Flag.Silent)
        self._client = client
        self._node = node
        self._periodicidad: dict[str, Any] = {}
        self._columna = ''

    def run(self) -> bool:
        wms_config = self._node.get('wmsConfig') or {}
        workspace = wms_config.get('geoserverWorkspace') or wms_config.get('workspace') or ''
        layer = wms_config.get('geoserverLayer') or ''
        if not workspace or not layer:
            return True
        try:
            self._periodicidad, columna = self._client.fetch_periodicity(
                workspace, layer, feedback=self._feedback)
        except MapaLabError as exc:
            self._error = str(exc)
            return False
        self._columna = columna or ''
        return True

    def finished(self, result: bool) -> None:
        if result:
            self.listo.emit(self._periodicidad, self._columna)
        elif not self.isCanceled():
            self.fallo.emit(self._error)


class Coordinador:

    def __init__(self) -> None:
        self._activas: dict[str, _TareaMapaLab] = {}

    def ocupado(self, clave: str) -> bool:
        return clave in self._activas

    def lanzar(self, clave: str, tarea: _TareaMapaLab,
               al_terminar: Callable[..., None],
               al_fallar: Callable[[str], None]) -> None:
        tarea.listo.connect(al_terminar)
        tarea.fallo.connect(al_fallar)
        tarea.taskCompleted.connect(lambda: self._liberar(clave, tarea))
        tarea.taskTerminated.connect(lambda: self._liberar(clave, tarea))
        self._activas[clave] = tarea
        QgsApplication.taskManager().addTask(tarea)

    def _liberar(self, clave: str, tarea: _TareaMapaLab) -> None:
        if self._activas.get(clave) is tarea:
            self._activas.pop(clave, None)

    def cancelar(self, clave: str) -> None:
        tarea = self._activas.pop(clave, None)
        if tarea is None:
            return
        try:
            tarea.cancel()
        except RuntimeError:
            pass

    def cancelar_todo(self) -> None:
        for clave in list(self._activas):
            self.cancelar(clave)
