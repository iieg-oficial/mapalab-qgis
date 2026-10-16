from typing import Optional

from qgis.core import QgsMapLayer, QgsProject

from ..config import NODE_ID_PROPERTY

GRUPO_PROPERTY: str = 'mapalab/grupoId'

SELECCION_PROPERTY: str = 'mapalab/seleccionDe'

PROPIEDADES: tuple[str, ...] = (NODE_ID_PROPERTY, GRUPO_PROPERTY, SELECCION_PROPERTY)


def capa_por_nodo(node_id: str) -> Optional[QgsMapLayer]:
    if not node_id:
        return None
    for capa in QgsProject.instance().mapLayers().values():
        if str(capa.customProperty(NODE_ID_PROPERTY) or '') == node_id:
            return capa
    return None


def quitar_nodo(node_id: str) -> int:
    project = QgsProject.instance()
    quitadas = 0
    for capa in list(project.mapLayers().values()):
        if str(capa.customProperty(NODE_ID_PROPERTY) or '') == node_id:
            project.removeMapLayer(capa.id())
            quitadas += 1
    return quitadas


def es_del_catalogo(capa: QgsMapLayer) -> bool:
    return bool(capa.customProperty(NODE_ID_PROPERTY) or capa.customProperty(GRUPO_PROPERTY))


def clave_de_capa(capa: QgsMapLayer) -> str:
    node_id = str(capa.customProperty(NODE_ID_PROPERTY) or '')
    if node_id:
        return node_id
    grupo = str(capa.customProperty(GRUPO_PROPERTY) or '')
    return f'{grupo}:{capa.name()}' if grupo else ''


def es_del_plugin(capa: QgsMapLayer) -> bool:
    return any(capa.customProperty(propiedad) for propiedad in PROPIEDADES)


def quitar_grupos_vacios() -> None:
    raiz = QgsProject.instance().layerTreeRoot()
    for nodo in list(raiz.children()):
        if hasattr(nodo, 'children') and not nodo.children() and nodo.name():
            raiz.removeChildNode(nodo)


def limpiar_selecciones() -> int:
    project = QgsProject.instance()
    capas = [capa for capa in project.mapLayers().values()
             if capa.customProperty(SELECCION_PROPERTY)]
    for capa in capas:
        project.removeMapLayer(capa.id())
    return len(capas)
