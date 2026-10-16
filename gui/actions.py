import os
from typing import Any, Optional

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QCoreApplication, Qt
from qgis.PyQt.QtGui import QCursor
from qgis.PyQt.QtWidgets import QApplication, QFileDialog, QWidget

from ..api.client import MapaLabClient
from ..layers.filtros import FILTRO_PROPERTY, Filtro, parametros, sufijo
from ..layers.grupos import add_group_layers, es_grupo
from ..layers.limites import aplicar_modo, modo_actual
from ..layers.proyecto import capa_por_nodo, limpiar_selecciones, quitar_nodo
from ..layers.seleccion import agregar
from ..layers.wms import build_wms_uri, capa_por_uri, crear_wms_layer, reconfigurar
from ..model.tree import clean_label, has_wfs, is_downloadable
from ..tasks import Coordinador, DescargarVectorTask, MetadataTask
from .ficha import abrir_ficha


COMPLETA_PROPERTY: str = 'mapalab/completa'


class LayerActions:

    def __init__(self, iface: Any, client: MapaLabClient, tareas: Coordinador) -> None:
        self._iface = iface
        self._client = client
        self._tareas = tareas
        self._ficha: Any = None
        self._ficha_feature: Any = None

    def _nombre(self, node: dict[str, Any], filtro: Optional[Filtro]) -> str:
        label = clean_label(node.get('label') or '')
        extra = sufijo(filtro, self._client.municipios) if filtro is not None else ''
        return f'{label} · {extra}' if extra else label

    def _busy(self, active: bool) -> None:
        if active:
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
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

    def add_group(self, node: dict[str, Any], completa: bool = False,
                  filtro: Optional[Filtro] = None) -> tuple[bool, str]:
        label = clean_label(node.get('label') or '')
        municipios = filtro.municipios if filtro is not None else []
        self._busy(True)
        try:
            agregadas, razon, aviso = add_group_layers(
                node, modo_actual(), completa, municipios, self._client.municipios)
        finally:
            self._busy(False)

        if agregadas == 0:
            return False, f'No se pudo agregar «{label}»: {razon}'
        return True, aviso

    def _uri(self, node: dict[str, Any], completa: bool, filtro: Optional[Filtro],
             columna: Optional[str]) -> tuple[str, Any]:
        params = parametros(node, filtro, self._client.municipios, columna, not completa)
        uri = build_wms_uri(node.get('wmsConfig') or {}, params.cql, params.time_value,
                            modo_actual(), params.estilo)
        return uri, params

    def add_as_wms(self, node: dict[str, Any], completa: bool = False,
                   filtro: Optional[Filtro] = None,
                   columna: Optional[str] = None) -> tuple[bool, str]:
        if es_grupo(node):
            return self.add_group(node, completa, filtro)

        label = clean_label(node.get('label') or '')
        uri, params = self._uri(node, completa, filtro, columna)
        existente = capa_por_uri(uri)
        if existente is not None:
            if self._iface is not None:
                self._iface.setActiveLayer(existente)
            return True, f'«{label}» ya está en el mapa.'

        self._busy(True)
        try:
            layer, reason = crear_wms_layer(node, params.cql, params.time_value, modo_actual(),
                                            self._nombre(node, filtro), params.estilo)
            if layer is None:
                return False, f'No se pudo agregar «{label}»: {reason}'
            layer.setCustomProperty(FILTRO_PROPERTY, (filtro or Filtro()).a_json())
            layer.setCustomProperty(COMPLETA_PROPERTY, completa)
            QgsProject.instance().addMapLayer(layer)
            self._attach_metadata(layer, node)
            if self._iface is not None:
                self._iface.setActiveLayer(layer)
        finally:
            self._busy(False)

        return True, ''

    def aplicar_filtro(self, node: dict[str, Any], filtro: Filtro,
                       columna: Optional[str]) -> tuple[bool, str]:
        capa = capa_por_nodo(str(node.get('id') or ''))
        if capa is None or capa.providerType() != 'wms':
            return True, ''
        completa = str(capa.customProperty(COMPLETA_PROPERTY)).lower() == 'true'
        uri, _ = self._uri(node, completa, filtro, columna)
        if uri != capa.source():
            reconfigurar(capa, uri, self._nombre(node, filtro))
        capa.setCustomProperty(FILTRO_PROPERTY, filtro.a_json())
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
                           completa: bool = False, filtro: Optional[Filtro] = None,
                           columna: Optional[str] = None,
                           ) -> tuple[Optional[DescargarVectorTask], str]:
        label = clean_label(node.get('label') or '')

        if not has_wfs(node):
            return None, f'«{label}» no está publicada como vectorial.'
        if not is_downloadable(node):
            return None, f'«{label}» no es descargable.'

        target_dir = self._target_dir(parent)
        if not target_dir:
            return None, ''

        params = parametros(node, filtro, self._client.municipios, columna, False)
        extra = sufijo(filtro, self._client.municipios) if filtro is not None else ''
        return DescargarVectorTask(self._client, node, target_dir, not completa,
                                   params.cql, extra), ''
