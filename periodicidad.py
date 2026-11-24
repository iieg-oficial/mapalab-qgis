from typing import Any

from qgis.PyQt.QtCore import pyqtSignal
from qgis.core import QgsTask

from .api.client import MapaLabClient, MapaLabError
from .layers.filtros import campo_municipio, resolver_campo
from .model.tree import typename
from .tasks import _TareaMapaLab


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
            if campo_municipio(self._node)[0]:
                resolver_campo(self._node, self._client.fetch_campos(
                    workspace, typename(self._node), feedback=self._feedback))
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
