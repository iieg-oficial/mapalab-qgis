import json
from typing import Any, Optional

from qgis.core import QgsMapLayer

FILTRO_PROPERTY: str = 'mapalab/filtro'

COLUMNA_FECHA: str = 'fecha'

TIPO_NOMBRE: str = 'nombre'

ZMG: tuple[str, ...] = (
    '14039', '14120', '14098', '14101', '14097', '14070', '14051', '14044', '14124')

MESES: tuple[str, ...] = (
    'ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic')

WORKSPACES_RASTER: frozenset = frozenset({'raster', 'lluvia', 'temperatura'})


class Filtro:

    def __init__(self, municipios: Optional[list[str]] = None, anio: Optional[int] = None,
                 mes: Optional[int] = None) -> None:
        self.municipios = list(municipios or [])
        self.anio = anio
        self.mes = mes if anio is not None else None

    def vacio(self) -> bool:
        return not self.municipios and self.anio is None

    def a_json(self) -> str:
        return json.dumps({'municipios': self.municipios, 'anio': self.anio, 'mes': self.mes})

    @classmethod
    def de_json(cls, texto: Any) -> Optional['Filtro']:
        try:
            datos = json.loads(str(texto or ''))
        except ValueError:
            return None
        if not isinstance(datos, dict):
            return None
        return cls(datos.get('municipios'), datos.get('anio'), datos.get('mes'))


def filtro_de_capa(capa: QgsMapLayer) -> Optional[Filtro]:
    return Filtro.de_json(capa.customProperty(FILTRO_PROPERTY))


def _comillas(valor: str) -> str:
    return "'" + str(valor).replace("'", "''") + "'"


def combinar(*partes: str) -> str:
    utiles = [parte for parte in partes if parte]
    if len(utiles) <= 1:
        return utiles[0] if utiles else ''
    return ' AND '.join(f'({parte})' for parte in utiles)


def es_raster_tiempo(node: dict[str, Any]) -> bool:
    return bool((node.get('wmsConfig') or {}).get('timeEnabled'))


def es_raster(node: dict[str, Any]) -> bool:
    wms_config = node.get('wmsConfig') or {}
    return es_raster_tiempo(node) or wms_config.get('workspace') in WORKSPACES_RASTER


def campo_municipio(node: dict[str, Any]) -> tuple[str, str]:
    meta = node.get('searchMeta') or {}
    if not meta.get('hasMunicipio') or es_raster(node):
        return '', ''
    return str(meta.get('municipioField') or ''), str(meta.get('municipioFieldType') or '')


def cql_municipio(node: dict[str, Any], claves: list[str],
                  catalogo: list[dict[str, Any]]) -> str:
    campo, tipo = campo_municipio(node)
    if not campo or not claves:
        return ''
    if tipo == TIPO_NOMBRE:
        nombres = {str(m.get('clave')): str(m.get('nombre') or '') for m in catalogo}
        valores = [nombres[clave] for clave in claves if nombres.get(clave)]
    else:
        valores = list(claves)
    if not valores:
        return ''
    return f"{campo} IN ({', '.join(_comillas(valor) for valor in valores)})"


def cql_fecha(columna: str, anio: Optional[int], mes: Optional[int]) -> str:
    if anio is None:
        return ''
    if mes is None:
        desde, hasta = f'{anio}-01-01', f'{anio + 1}-01-01'
    else:
        siguiente = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
        desde, hasta = f'{anio}-{mes:02d}-01', f'{siguiente[0]}-{siguiente[1]:02d}-01'
    columna = columna or COLUMNA_FECHA
    return f"{columna} >= '{desde}' AND {columna} < '{hasta}'"


def periodicidad_raster(node: dict[str, Any]) -> dict[str, Any]:
    datos = node.get('rasterPeriodicity')
    return datos if isinstance(datos, dict) else {}


def valor_time(node: dict[str, Any], anio: Optional[int], mes: Optional[int]) -> str:
    if anio is None:
        return ''
    meses = periodicidad_raster(node).get(str(anio)) or {}
    if mes is None:
        if not meses:
            return ''
        mes = max(int(clave) for clave in meses)
    return str(meses.get(str(mes)) or f'{anio}-{mes:02d}-01')


def estilo_por_fecha(node: dict[str, Any], time_value: str) -> str:
    patron = str((node.get('wmsConfig') or {}).get('timeStylePattern') or '')
    if not patron or not time_value:
        return ''
    anio, mes = time_value.split('-')[:2]
    return patron.replace('{year}', anio).replace('{month}', mes)


def anios_y_meses(periodicidad: Optional[dict[str, Any]]) -> dict[int, list[int]]:
    salida: dict[int, list[int]] = {}
    for anio, meses in (periodicidad or {}).items():
        try:
            salida[int(anio)] = sorted(int(mes) for mes in (meses or {}))
        except (TypeError, ValueError):
            continue
    return salida


def fecha_por_defecto(node: dict[str, Any], disponibles: dict[int, list[int]],
                      ) -> tuple[Optional[int], Optional[int]]:
    defecto = node.get('defaultDate')
    if es_raster_tiempo(node) and not defecto:
        defecto = 'latest'
    if not defecto:
        return None, None
    anios = sorted(disponibles, reverse=True)
    if defecto == 'latest':
        if not anios:
            return None, None
        meses = disponibles[anios[0]]
        return anios[0], (meses[-1] if meses else None)
    if not isinstance(defecto, dict) or not defecto.get('year'):
        return None, None
    objetivo, mes = int(defecto['year']), defecto.get('month')
    if not anios or objetivo in disponibles:
        return objetivo, mes
    anio = next((a for a in anios if a < objetivo), anios[0])
    if mes is not None and mes not in disponibles[anio]:
        mes = disponibles[anio][-1] if disponibles[anio] else None
    return anio, mes


def columna_de(node: dict[str, Any], columna_servidor: Optional[str]) -> str:
    defecto = node.get('defaultDate')
    if isinstance(defecto, dict) and defecto.get('column'):
        return str(defecto['column'])
    return columna_servidor or COLUMNA_FECHA


def sufijo(filtro: Filtro, catalogo: list[dict[str, Any]]) -> str:
    partes: list[str] = []
    if filtro.anio is not None:
        partes.append(f'{MESES[filtro.mes - 1]} {filtro.anio}' if filtro.mes else str(filtro.anio))
    if filtro.municipios:
        if sorted(filtro.municipios) == sorted(ZMG):
            partes.append('ZMG')
        else:
            nombres = {str(m.get('clave')): str(m.get('nombre') or '') for m in catalogo}
            elegidos = [nombres.get(clave) or clave for clave in filtro.municipios]
            resto = f' +{len(elegidos) - 2}' if len(elegidos) > 2 else ''
            partes.append(', '.join(elegidos[:2]) + resto)
    return ' · '.join(partes)


class Parametros:

    def __init__(self, cql: str = '', time_value: str = '', estilo: str = '') -> None:
        self.cql = cql
        self.time_value = time_value
        self.estilo = estilo


def parametros(node: dict[str, Any], filtro: Optional[Filtro], catalogo: list[dict[str, Any]],
               columna: Optional[str], con_base: bool = True) -> Parametros:
    base = str((node.get('wmsConfig') or {}).get('cqlFilter') or '') if con_base else ''
    if filtro is None:
        return Parametros(base)
    municipio = cql_municipio(node, filtro.municipios, catalogo)
    if es_raster_tiempo(node):
        time_value = valor_time(node, filtro.anio, filtro.mes)
        return Parametros(combinar(base, municipio), time_value,
                          estilo_por_fecha(node, time_value))
    fecha = cql_fecha(columna_de(node, columna), filtro.anio, filtro.mes)
    return Parametros(combinar(base, municipio, fecha))
