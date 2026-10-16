import json
import math
import re
from typing import Any, Iterator, Optional
from urllib.parse import parse_qs, quote, urlsplit

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsJsonUtils,
    QgsLayerTreeGroup,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtCore import QVariant

from ..model.tree import clean_label
from .filtros import combinar, cql_municipio, es_raster_tiempo, estilo_por_fecha
from .grupos import hojas_de
from .wms import crear_wms_layer

CODIGO_RE = re.compile(r'^[a-z2-7]{10}$')

FECHA_RE = re.compile(r'^\d{4}-\d{2}-\d{2}')

PARAMETROS_URL: tuple[str, ...] = ('s', 'share')

RESOLUCION_Z0: float = 156543.03392804097

MAPA_BASE: tuple[str, str] = (
    'OpenStreetMap', 'https://tile.openstreetmap.org/{z}/{x}/{y}.png')

MAPAS_BASE_DEL_VISOR: frozenset = frozenset({'voyager', 'position', 'oscuro'})

GEOMETRIAS: dict[str, str] = {
    'Point': 'Point', 'MultiPoint': 'Point', 'LineString': 'LineString',
    'MultiLineString': 'LineString', 'Polygon': 'Polygon', 'MultiPolygon': 'Polygon',
}


def codigo_de(texto: str) -> str:
    limpio = (texto or '').strip()
    if CODIGO_RE.match(limpio):
        return limpio
    consulta = parse_qs(urlsplit(limpio).query)
    for parametro in PARAMETROS_URL:
        for valor in consulta.get(parametro) or []:
            if CODIGO_RE.match(valor.strip()):
                return valor.strip()
    return ''


class CapaCompartida:

    def __init__(self, node: dict[str, Any], visible: bool, opacidad: float, cql: str,
                 fecha: str, time_value: str) -> None:
        self.node = node
        self.visible = visible
        self.opacidad = opacidad
        self.cql = cql
        self.fecha = fecha
        self.time_value = time_value
        self.nota = '' if visible else 'oculta'
        self.falta_fecha = bool(node.get('defaultDate')) and not fecha and not time_value

    def etiqueta(self) -> str:
        return clean_label(str(self.node.get('label') or ''))


class Plan:

    def __init__(self, codigo: str) -> None:
        self.codigo = codigo
        self.capas: list[CapaCompartida] = []
        self.faltantes: list[str] = []
        self.municipios: list[str] = []
        self.modo: Optional[str] = None
        self.vista: dict[str, Any] = {}
        self.mapa_base = ''
        self.anotaciones: list[dict[str, Any]] = []


def _nodos(nodos: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for nodo in nodos:
        yield nodo
        yield from _nodos(nodo.get('children') or [])


def resolver(ref: str, arbol: list[dict[str, Any]]) -> Optional[dict[str, Any]]:
    buscado = str(ref or '').strip().lower()
    if not buscado:
        return None
    por_alias: Optional[dict[str, Any]] = None
    for nodo in _nodos(arbol):
        if str(nodo.get('id') or '').lower() == buscado:
            return nodo
        alias = [str(nodo.get('slug') or '')] + [str(a) for a in nodo.get('aliases') or []]
        if por_alias is None and buscado in (a.lower() for a in alias if a):
            por_alias = nodo
    return por_alias


def _numero(valor: Any, defecto: float) -> float:
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return defecto
    return numero if math.isfinite(numero) else defecto


def _capa(node: dict[str, Any], entrada: dict[str, Any]) -> CapaCompartida:
    filtros = entrada.get('filters') if isinstance(entrada.get('filters'), dict) else {}
    utiles = {clave: str(valor) for clave, valor in filtros.items()
              if isinstance(valor, str) and valor.strip() and not clave.startswith('_')}
    fecha = utiles.pop('date', '')
    time_value = ''
    if es_raster_tiempo(node):
        time_value = fecha if FECHA_RE.match(fecha) else ''
        fecha = ''
    utiles.pop('municipio', None)
    cql = combinar(*utiles.values(), fecha)
    opacidad = min(1.0, max(0.0, _numero(entrada.get('opacity'), 1.0)))
    return CapaCompartida(node, entrada.get('visible') is not False, opacidad, cql, fecha,
                          time_value)


def planear(codigo: str, sobre: dict[str, Any], arbol: list[dict[str, Any]]) -> Plan:
    plan = Plan(codigo)
    payload = sobre.get('payload') or {}
    comun = payload
    entradas: list[Any] = payload.get('layers') or []
    if sobre.get('kind') == 'swipe':
        comun = payload.get('shared') or {}
        panel = payload.get('paneB' if payload.get('activeSlot') == 'B' else 'paneA') or {}
        entradas = panel.get('layers') or []

    resueltas: list[tuple[dict[str, Any], Optional[dict[str, Any]]]] = []
    explicitas: dict[str, dict[str, Any]] = {}
    for entrada in entradas:
        if not isinstance(entrada, dict):
            continue
        node = resolver(str(entrada.get('slug') or ''), arbol)
        resueltas.append((entrada, node))
        if node is not None and node.get('wmsConfig'):
            explicitas.setdefault(str(node.get('id') or ''), entrada)

    vistos: set[str] = set()
    for entrada, node in resueltas:
        if node is None:
            plan.faltantes.append(str(entrada.get('slug') or ''))
            continue
        for hoja in hojas_de(node):
            clave = str(hoja.get('id') or '')
            if clave not in vistos:
                vistos.add(clave)
                plan.capas.append(_capa(hoja, explicitas.get(clave, entrada)))

    municipios = comun.get('municipios') if isinstance(comun.get('municipios'), dict) else {}
    plan.municipios = [str(c) for c in municipios.get('selected') or [] if str(c).isdigit()]
    plan.modo = municipios.get('source') if municipios.get('source') in ('iieg', 'inegi') else None
    plan.vista = comun.get('view') if isinstance(comun.get('view'), dict) else {}
    plan.mapa_base = str(comun.get('basemap') or '')
    anotaciones = payload.get('annotations') or comun.get('annotations') or []
    plan.anotaciones = [a for a in anotaciones if isinstance(a, dict)
                        and isinstance(a.get('geometry'), dict)]
    return plan


def _capa_wms(capa: CapaCompartida, plan: Plan,
              catalogo: list[dict[str, Any]]) -> Optional[QgsRasterLayer]:
    base = str((capa.node.get('wmsConfig') or {}).get('cqlFilter') or '')
    municipio = cql_municipio(capa.node, plan.municipios, catalogo)
    layer, _ = crear_wms_layer(capa.node, combinar(base, capa.cql, municipio),
                               capa.time_value or None, plan.modo, capa.etiqueta(),
                               estilo_por_fecha(capa.node, capa.time_value))
    if layer is not None:
        layer.renderer().setOpacity(capa.opacidad)
    return layer


def _mapa_base(clave: str) -> Optional[QgsRasterLayer]:
    if clave not in MAPAS_BASE_DEL_VISOR:
        return None
    nombre, url = MAPA_BASE
    capa = QgsRasterLayer(f'type=xyz&url={quote(url, safe="")}&zmin=0&zmax=19', nombre, 'wms')
    return capa if capa.isValid() else None


def _anotaciones(anotaciones: list[dict[str, Any]]) -> list[QgsVectorLayer]:
    por_tipo: dict[str, list[QgsFeature]] = {}
    capas: dict[str, QgsVectorLayer] = {}
    for anotacion in anotaciones:
        tipo = GEOMETRIAS.get(str(anotacion['geometry'].get('type') or ''))
        geometria = QgsJsonUtils.geometryFromGeoJson(json.dumps(anotacion['geometry']))
        if tipo is None or geometria is None or geometria.isEmpty():
            continue
        if tipo not in capas:
            capa = QgsVectorLayer(f'{tipo}?crs=EPSG:4326', f'Anotaciones · {tipo}', 'memory')
            capa.dataProvider().addAttributes(
                [QgsField('tipo', QVariant.String), QgsField('texto', QVariant.String)])
            capa.updateFields()
            capas[tipo] = capa
        feature = QgsFeature(capas[tipo].fields())
        feature.setGeometry(QgsGeometry(geometria))
        feature['tipo'] = str(anotacion.get('type') or '')
        feature['texto'] = str(anotacion.get('label') or anotacion.get('emoji') or '')[:200]
        por_tipo.setdefault(tipo, []).append(feature)
    for tipo, capa in capas.items():
        capa.dataProvider().addFeatures(por_tipo[tipo])
        capa.updateExtents()
        if tipo == 'Point':
            etiquetas = QgsPalLayerSettings()
            etiquetas.fieldName = 'texto'
            capa.setLabeling(QgsVectorLayerSimpleLabeling(etiquetas))
            capa.setLabelsEnabled(True)
    return list(capas.values())


def encuadrar(canvas: Any, vista: dict[str, Any]) -> None:
    lat, lon = _numero(vista.get('lat'), math.nan), _numero(vista.get('lon'), math.nan)
    zoom = _numero(vista.get('zoom'), math.nan)
    if math.isnan(lat) or math.isnan(lon) or math.isnan(zoom):
        return
    proyecto = QgsProject.instance()
    web = QgsCoordinateReferenceSystem('EPSG:3857')
    centro = QgsCoordinateTransform(QgsCoordinateReferenceSystem('EPSG:4326'), web,
                                    proyecto).transform(QgsPointXY(lon, lat))
    resolucion = RESOLUCION_Z0 / (2 ** zoom)
    medio_x, medio_y = canvas.width() * resolucion / 2, canvas.height() * resolucion / 2
    rect = QgsRectangle(centro.x() - medio_x, centro.y() - medio_y,
                        centro.x() + medio_x, centro.y() + medio_y)
    destino = canvas.mapSettings().destinationCrs()
    canvas.setExtent(QgsCoordinateTransform(web, destino, proyecto).transformBoundingBox(rect))
    canvas.setRotation(math.degrees(_numero(vista.get('rotation'), 0.0)))
    canvas.refresh()


def construir(plan: Plan, catalogo: list[dict[str, Any]], con_mapa_base: bool,
              con_anotaciones: bool) -> tuple[int, list[str]]:
    proyecto = QgsProject.instance()
    grupo: QgsLayerTreeGroup = proyecto.layerTreeRoot().insertGroup(
        0, f'Mapa compartido · {plan.codigo}')
    fallidas: list[str] = []
    agregadas = 0

    extras: list[Any] = _anotaciones(plan.anotaciones) if con_anotaciones else []
    for capa_extra in extras:
        proyecto.addMapLayer(capa_extra, False)
        grupo.addLayer(capa_extra)

    for capa in plan.capas:
        layer = _capa_wms(capa, plan, catalogo)
        if layer is None:
            fallidas.append(capa.etiqueta())
            continue
        proyecto.addMapLayer(layer, False)
        grupo.addLayer(layer).setItemVisibilityChecked(capa.visible)
        agregadas += 1

    base = _mapa_base(plan.mapa_base) if con_mapa_base else None
    if base is not None:
        proyecto.addMapLayer(base, False)
        grupo.addLayer(base)

    if not grupo.children():
        proyecto.layerTreeRoot().removeChildNode(grupo)
    return agregadas, fallidas
