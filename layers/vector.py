import os
import re
from typing import Any, Callable, Optional
from urllib.parse import urlencode

from qgis.core import QgsFeedback, QgsProject, QgsVectorLayer

from ..almacen import escribir_atomico
from ..api.client import MapaLabClient, MapaLabError
from ..config import DOWNLOAD_CRS, DOWNLOAD_TIMEOUT_MS
from ..model.tree import clean_label, typename

GPKG_FORMAT: str = 'geopackage'

FIRMA_SQLITE: bytes = b'SQLite format 3'

MAX_VARIANTES: int = 999


def _safe_name(value: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9_.-]+', '_', value)
    return cleaned.strip('_') or 'capa'


def _excepcion(contenido: bytes) -> str:
    texto = contenido[:4000].decode('utf-8', errors='replace')
    encontrada = re.search(r'<(?:ows:)?ExceptionText>(.*?)</', texto, re.DOTALL)
    return encontrada.group(1).strip()[:300] if encontrada else ''


def ruta_libre(target_dir: str, nombre: str) -> str:
    destino = os.path.join(target_dir, f'{nombre}.gpkg')
    for numero in range(2, MAX_VARIANTES + 1):
        if not os.path.exists(destino):
            return destino
        destino = os.path.join(target_dir, f'{nombre}_{numero}.gpkg')
    return destino


def build_wfs_url(wms_config: dict[str, Any], type_name: str, cql_filter: str = '') -> str:
    params: dict[str, str] = {
        'service': 'WFS',
        'version': '2.0.0',
        'request': 'GetFeature',
        'typeNames': type_name,
        'outputFormat': GPKG_FORMAT,
        'srsName': DOWNLOAD_CRS,
    }
    if cql_filter:
        params['CQL_FILTER'] = cql_filter
    return f"{wms_config.get('wfsUrl') or ''}?{urlencode(params)}"


def download_vector(node: dict[str, Any], client: MapaLabClient, target_dir: str,
                    apply_node_filter: bool = False,
                    extra_cql: str = '',
                    sufijo: str = '',
                    feedback: Optional[QgsFeedback] = None,
                    on_progress: Optional[Callable[[int, int], None]] = None,
                    ) -> tuple[Optional[str], str]:
    wms_config = node.get('wmsConfig') or {}
    type_name = typename(node)
    if not type_name:
        return None, 'La capa no tiene nombre WFS.'

    filters: list[str] = []
    if apply_node_filter and wms_config.get('cqlFilter'):
        filters.append(wms_config['cqlFilter'])
    if extra_cql:
        filters.append(extra_cql)

    if len(filters) == 1:
        cql_filter = filters[0]
    elif filters:
        cql_filter = ' AND '.join(f'({item})' for item in filters)
    else:
        cql_filter = ''

    url = build_wfs_url(wms_config, type_name, cql_filter)
    nombre = _safe_name(type_name)
    if apply_node_filter and wms_config.get('cqlFilter'):
        nombre = f"{nombre}_{_safe_name(str(node.get('id') or ''))}"
    if sufijo:
        nombre = f'{nombre}_{_safe_name(sufijo)}'

    try:
        contenido = client.descargar(
            url, DOWNLOAD_TIMEOUT_MS, feedback=feedback, on_progress=on_progress)
    except MapaLabError as exc:
        return None, str(exc)

    if not contenido:
        return None, 'El servidor devolvió una respuesta vacía.'
    if not contenido.startswith(FIRMA_SQLITE):
        return None, f'El servidor no devolvió un GeoPackage. {_excepcion(contenido)}'.strip()

    destination = ruta_libre(target_dir, nombre)
    if os.path.exists(destination) or not escribir_atomico(destination, contenido):
        return None, f'No se pudo escribir en {target_dir}.'

    return destination, ''


def add_vector_layer(path: str, node: dict[str, Any]) -> Optional[QgsVectorLayer]:
    name = clean_label(node.get('label') or 'MapaLab')
    layer = QgsVectorLayer(path, name, 'ogr')
    if not layer.isValid():
        return None

    QgsProject.instance().addMapLayer(layer)
    return layer
