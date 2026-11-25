from typing import Any, Optional

from ..config import get_base_url
from .tree import TIPO_CATEGORIA, TIPO_ETIQUETA, TIPO_TEMA

MODO_LITE: str = 'lite'


def _clave(node: dict[str, Any]) -> Optional[tuple[str, str]]:
    wms_config = node.get('wmsConfig') or {}
    workspace = wms_config.get('workspace') or wms_config.get('geoserverWorkspace')
    layer = wms_config.get('geoserverLayer') or wms_config.get('wmsGroup')
    return (workspace, layer) if workspace and layer else None


def _indice(nodes: list[dict[str, Any]],
            indice: Optional[dict[tuple[str, str], dict[str, Any]]] = None,
            ) -> dict[tuple[str, str], dict[str, Any]]:
    indice = {} if indice is None else indice
    for node in nodes:
        clave = _clave(node)
        if clave and clave not in indice:
            indice[clave] = node
        _indice(node.get('children') or [], indice)
    return indice


def _nodo(capa: dict[str, Any], posicion: int, padre: str,
          indice: dict[tuple[str, str], dict[str, Any]],
          permitir_categoria: bool) -> Optional[dict[str, Any]]:
    alias = str(capa.get('alias') or '').strip()
    tipo = capa.get('tipo') or 'capa'
    if tipo == 'etiqueta':
        nodo_id = f'{padre}-etiqueta-{posicion}'
        return {'id': nodo_id, 'label': alias, 'nodeType': TIPO_ETIQUETA, 'children': []}
    if tipo == 'categoria':
        if not permitir_categoria:
            return None
        nodo_id = f'{padre}-categoria-{posicion}'
        hijos = _hijos(capa.get('capas') or [], nodo_id, indice, False)
        if not hijos:
            return None
        return {'id': nodo_id, 'label': alias, 'nodeType': TIPO_CATEGORIA, 'children': hijos}
    capa_del_arbol = indice.get((capa.get('workspace') or '', capa.get('layer') or ''))
    if capa_del_arbol is None:
        return None
    return {**capa_del_arbol, 'label': alias} if alias else capa_del_arbol


def _hijos(capas: list[dict[str, Any]], padre: str,
           indice: dict[tuple[str, str], dict[str, Any]],
           permitir_categoria: bool) -> list[dict[str, Any]]:
    nodos = [_nodo(capa, posicion, padre, indice, permitir_categoria)
             for posicion, capa in enumerate(capas) if isinstance(capa, dict)]
    return [nodo for nodo in nodos if nodo is not None]


def _tiene_capas(nodos: list[dict[str, Any]]) -> bool:
    return any(nodo.get('wmsConfig') or _tiene_capas(nodo.get('children') or [])
               for nodo in nodos)


def temas_de_eventos(eventos: list[dict[str, Any]],
                     arbol: list[dict[str, Any]]) -> list[dict[str, Any]]:
    base_url = get_base_url()
    indice = _indice(arbol)
    temas: list[dict[str, Any]] = []
    for evento in eventos:
        if evento.get('modo') == MODO_LITE:
            continue
        nodo_id = f'evento-{evento.get("id")}'
        hijos = _hijos(evento.get('capas') or [], nodo_id, indice, True)
        if not _tiene_capas(hijos):
            continue
        icono = str(evento.get('iconoUrl') or '')
        temas.append({
            'id': nodo_id,
            'label': str(evento.get('titulo') or ''),
            'nodeType': TIPO_TEMA,
            'iconUrl': f'{base_url}{icono}' if icono.startswith('/') else icono,
            'children': hijos,
        })
    return temas
