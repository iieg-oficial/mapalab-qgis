from typing import Any, Callable, Optional

from qgis.core import QgsCoordinateReferenceSystem, QgsMapLayer, QgsProject
from qgis.gui import QgsMapTool, QgsMapToolPan

from ..api.client import MapaLabClient
from ..config import CAPAS_BASE, NODE_ID_PROPERTY
from ..layers.featureinfo import config_de_capa, features_de_json, url_de_consulta
from ..layers.limites import modo_actual
from ..layers.proyecto import capa_por_nodo, clave_de_capa, es_del_catalogo
from ..model.tree import clean_label
from ..tasks import ConsultaTask, Coordinador

CLAVE_TAREA: str = 'consulta'

IDS_BASE: frozenset = frozenset(node_id for ids in CAPAS_BASE.values() for node_id in ids)


def _es_base(capa: QgsMapLayer) -> bool:
    return str(capa.customProperty(NODE_ID_PROPERTY) or '') in IDS_BASE


def capas_visibles_del_catalogo() -> list[QgsMapLayer]:
    capas: list[QgsMapLayer] = []
    for nodo in QgsProject.instance().layerTreeRoot().findLayers():
        capa = nodo.layer()
        if capa is not None and nodo.isVisible() and es_del_catalogo(capa):
            capas.append(capa)
    tematicas = [capa for capa in capas if not _es_base(capa)]
    return tematicas or capas


class HerramientaConsulta(QgsMapTool):

    def __init__(self, canvas: Any, client: MapaLabClient, tareas: Coordinador,
                 nodo_actual: Callable[[], Optional[dict[str, Any]]],
                 al_consultar: Callable[[Optional[tuple], str], None]) -> None:
        super().__init__(canvas)
        self._client = client
        self._tareas = tareas
        self._nodo_actual = nodo_actual
        self._al_consultar = al_consultar

    def canvasReleaseEvent(self, evento: Any) -> None:
        x, y = int(evento.x()), int(evento.y())
        node = self._nodo_actual()

        if node and node.get('wmsConfig'):
            capa = capa_por_nodo(str(node.get('id') or ''))
            if capa is None:
                self._consultar([_Destino(str(node.get('id') or ''),
                                          clean_label(node.get('label') or ''),
                                          node['wmsConfig'], None)], x, y)
            else:
                self._consultar([_destino_de_capa(capa)], x, y)
            return

        activa = self._capa_activa()
        capas = [activa] if activa is not None else capas_visibles_del_catalogo()
        if not capas:
            self._al_consultar(None, 'Selecciona una capa del árbol o agrégala al mapa.')
            return
        self._consultar([_destino_de_capa(capa) for capa in capas], x, y)

    def _capa_activa(self) -> Optional[QgsMapLayer]:
        capa = self.canvas().currentLayer()
        if capa is None or not es_del_catalogo(capa):
            return None
        return capa

    def _consultar(self, destinos: list['_Destino'], x: int, y: int) -> None:
        canvas = self.canvas()
        settings = canvas.mapSettings()
        crs: QgsCoordinateReferenceSystem = settings.destinationCrs()
        modo = modo_actual()
        self._tareas.cancelar(CLAVE_TAREA)

        def siguiente(pendientes: list[_Destino]) -> None:
            if not pendientes:
                self._al_consultar(None, 'Sin elementos de MapaLab en ese punto.')
                return
            destino, resto = pendientes[0], pendientes[1:]
            url = url_de_consulta(destino.config, settings.extent(), canvas.width(),
                                  canvas.height(), crs.authid(), x, y, modo, destino.extra)
            if not url:
                siguiente(resto)
                return

            def al_responder(texto: str) -> None:
                features = features_de_json(texto)
                if not features:
                    siguiente(resto)
                    return
                self._al_consultar((destino.clave, destino.nombre, crs, features), '')

            self._tareas.lanzar(CLAVE_TAREA, ConsultaTask(self._client, url), al_responder,
                                lambda aviso: self._al_consultar(None, aviso))

        self._al_consultar(None, 'Consultando…')
        siguiente(destinos)


class _Destino:

    def __init__(self, clave: str, nombre: str, config: dict[str, Any],
                 extra: Optional[dict[str, str]]) -> None:
        self.clave = clave
        self.nombre = nombre
        self.config = config
        self.extra = extra


def _destino_de_capa(capa: QgsMapLayer) -> _Destino:
    config, extra = config_de_capa(capa)
    return _Destino(clave_de_capa(capa), capa.name(), config, extra)


class ControlConsulta:

    def __init__(self, iface: Any, crear: Callable[[Any], HerramientaConsulta]) -> None:
        self._iface = iface
        self._crear = crear
        self._herramienta: Optional[HerramientaConsulta] = None

    def _canvas(self) -> Any:
        return self._iface.mapCanvas() if self._iface is not None else None

    def _herramienta_de(self, canvas: Any) -> HerramientaConsulta:
        if self._herramienta is None:
            self._herramienta = self._crear(canvas)
        return self._herramienta

    def _cedible(self, actual: Any) -> bool:
        if actual is None or isinstance(actual, QgsMapToolPan):
            return True
        if actual is self._herramienta:
            return True
        accion = actual.action()
        return accion is not None and accion in (
            self._iface.actionPan(), self._iface.actionIdentify())

    def activar(self, forzar: bool = False) -> None:
        canvas = self._canvas()
        if canvas is None:
            return
        actual = canvas.mapTool()
        if forzar or self._cedible(actual):
            canvas.setMapTool(self._herramienta_de(canvas))

    def desactivar(self) -> None:
        canvas = self._canvas()
        if canvas is None or self._herramienta is None:
            return
        if canvas.mapTool() is self._herramienta:
            self._iface.actionPan().trigger()
        canvas.unsetMapTool(self._herramienta)
