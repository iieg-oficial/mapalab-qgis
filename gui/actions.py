import os
from typing import Any, Optional

from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtWidgets import QApplication, QFileDialog, QWidget

from ..api.client import MapaLabClient
from ..layers.grupos import add_group_layers, es_grupo
from ..layers.limites import aplicar_modo, modo_actual
from ..layers.proyecto import limpiar_selecciones, quitar_nodo
from ..layers.seleccion import agregar
from ..layers.wms import add_wms_layer, capa_existente
from ..model.tree import clean_label, has_wfs, is_downloadable
from ..tasks import Coordinador, DescargarVectorTask, MetadataTask
from .ficha import abrir_ficha


class LayerActions:

    def __init__(self, iface: Any, client: MapaLabClient, tareas: Coordinador) -> None:
        self._iface = iface
        self._client = client
        self._tareas = tareas
        self._ficha: Any = None
        self._ficha_feature: Any = None

    def _busy(self, active: bool) -> None:
        if active:
            QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        else:
            QApplication.restoreOverrideCursor()
        QCoreApplication.processEvents()

    def _attach_metadata(self, layer: Any, node: dict[str, Any]) -> None:
        tarea = MetadataTask(self._client, node, layer.id())
        self._tareas.lanzar(f'metadata:{layer.id()}', tarea, lambda _: None, lambda _: None)

    def clear_selections(self) -> int:
        return self._quitar(limpiar_selecciones())

    def _quitar(self, quitadas: int) -> int:
        if quitadas and self._iface is not None:
            self._iface.mapCanvas().refresh()
        return quitadas

    def remove_node(self, node_id: str) -> int:
        return self._quitar(quitar_nodo(node_id))

    def add_group(self, node: dict[str, Any], completa: bool = False) -> tuple[bool, str]:
        label = clean_label(node.get('label') or '')
        self._busy(True)
        try:
            agregadas, razon, aviso = add_group_layers(node, modo_actual(), completa)
        finally:
            self._busy(False)

        if agregadas == 0:
            return False, f'No se pudo agregar «{label}»: {razon}'
        return True, aviso

    def add_as_wms(self, node: dict[str, Any], completa: bool = False) -> tuple[bool, str]:
        if es_grupo(node):
            return self.add_group(node, completa)

        label = clean_label(node.get('label') or '')
        modo = modo_actual()
        existente = capa_existente(node, apply_node_filter=not completa, modo=modo)
        if existente is not None:
            if self._iface is not None:
                self._iface.setActiveLayer(existente)
            return True, f'«{label}» ya está en el mapa.'

        self._busy(True)
        try:
            layer, reason = add_wms_layer(node, apply_node_filter=not completa, modo=modo)
            if layer is None:
                return False, f'No se pudo agregar «{label}»: {reason}'
            self._attach_metadata(layer, node)
            if self._iface is not None:
                self._iface.setActiveLayer(layer)
        finally:
            self._busy(False)

        return True, ''

    def abrir_feature(self, datos: tuple) -> tuple[bool, str]:
        node_id, nombre, crs, elementos = datos
        capa: Any = None
        fids: list[int] = []
        fallo = ''

        for feature, marca in elementos:
            destino, fid, error = agregar(node_id, nombre, crs, feature, marca)
            if destino is None:
                fallo = error
                continue
            capa = destino
            fids.append(fid)

        if capa is None or not fids:
            return False, fallo or 'No se pudo consultar ese elemento.'

        capa.selectByIds(fids)
        if self._iface is not None:
            self._ficha_feature = capa.getFeature(fids[0])
            self._ficha = abrir_ficha(capa, self._ficha_feature, self._iface.mainWindow())
        return True, ''

    def set_base_mode(self, arbol: list[dict[str, Any]], modo: str) -> tuple[bool, str]:
        self._busy(True)
        try:
            return aplicar_modo(arbol, modo)
        finally:
            self._busy(False)

    def _target_dir(self, parent: Optional[QWidget]) -> str:
        return QFileDialog.getExistingDirectory(
            parent, 'Dónde guardar el GeoPackage', os.path.expanduser('~'))

    def download_as_vector(self, node: dict[str, Any], parent: Optional[QWidget] = None,
                           completa: bool = False,
                           ) -> tuple[Optional[DescargarVectorTask], str]:
        label = clean_label(node.get('label') or '')

        if not has_wfs(node):
            return None, f'«{label}» no está publicada como vectorial.'
        if not is_downloadable(node):
            return None, f'«{label}» no es descargable.'

        target_dir = self._target_dir(parent)
        if not target_dir:
            return None, ''

        return DescargarVectorTask(self._client, node, target_dir, not completa), ''
