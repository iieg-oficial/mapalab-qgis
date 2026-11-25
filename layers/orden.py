from typing import Any

from qgis.core import (
    QgsCoordinateTransform,
    QgsLayerTree,
    QgsLayerTreeLayer,
    QgsMapLayer,
    QgsProject,
    QgsRectangle,
)

from ..config import NODE_ID_PROPERTY
from .filtros import filtro_de_capa
from .proyecto import GRUPO_PROPERTY
from .zoom import ajustar_a

AIRE: float = 1.08


def clave_de_fila(capa: QgsMapLayer) -> str:
    grupo = str(capa.customProperty(GRUPO_PROPERTY) or '')
    return grupo or str(capa.customProperty(NODE_ID_PROPERTY) or '')


def nodos_de_fila(clave: str) -> list[QgsLayerTreeLayer]:
    return [nodo for nodo in QgsProject.instance().layerTreeRoot().findLayers()
            if nodo.layer() is not None and clave_de_fila(nodo.layer()) == clave]


def _es_de(nodo: Any, clave: str) -> bool:
    capas = nodo.findLayers() if QgsLayerTree.isGroup(nodo) else [nodo]
    return bool(capas) and all(
        capa.layer() is not None and clave_de_fila(capa.layer()) == clave for capa in capas)


def _unidades(clave: str) -> list[Any]:
    unidades: list[Any] = []
    for nodo in nodos_de_fila(clave):
        unidad = nodo
        padre = unidad.parent()
        while padre is not None and padre.parent() is not None and _es_de(padre, clave):
            unidad = padre
            padre = unidad.parent()
        if not any(unidad is vista for vista in unidades):
            unidades.append(unidad)
    return unidades


def mover_fila(claves: list[str], origen: int, destino: int) -> bool:
    if not 0 <= origen < len(claves) or not 0 <= destino <= len(claves):
        return False
    moviles = _unidades(claves[origen])
    if destino < len(claves):
        anclas, desfase = _unidades(claves[destino]), 0
    else:
        anclas, desfase = _unidades(claves[-1]), 1
    if not moviles or not anclas:
        return False
    ancla = anclas[0] if desfase == 0 else anclas[-1]
    padre = ancla.parent()
    if padre is None:
        return False
    hijos = padre.children()
    indice = next((i for i, hijo in enumerate(hijos) if hijo is ancla), len(hijos)) + desfase
    for paso, unidad in enumerate(moviles):
        padre.insertChildNode(indice + paso, unidad.clone())
    for unidad in moviles:
        unidad.parent().removeChildNode(unidad)
    return True


def encuadrar_fila(canvas: Any, clave: str, ocupado: int = 0) -> bool:
    destino = canvas.mapSettings().destinationCrs()
    contexto = QgsProject.instance().transformContext()
    extension = QgsRectangle()
    for nodo in nodos_de_fila(clave):
        capa = nodo.layer()
        caja = capa.extent()
        if caja.isNull() or caja.isEmpty():
            continue
        if capa.crs() != destino:
            caja = QgsCoordinateTransform(capa.crs(), destino, contexto).transformBoundingBox(caja)
        extension.combineExtentWith(caja)
    if extension.isNull() or extension.isEmpty():
        return False
    extension.scale(AIRE)
    return ajustar_a(canvas, extension, ocupado)


def municipios_de_fila(clave: str) -> list[str]:
    municipios: list[str] = []
    for nodo in nodos_de_fila(clave):
        filtro = filtro_de_capa(nodo.layer())
        for municipio in (filtro.municipios if filtro is not None else []):
            if municipio not in municipios:
                municipios.append(municipio)
    return municipios
