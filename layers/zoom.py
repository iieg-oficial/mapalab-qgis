from typing import Any

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
)

CRS_CAJAS: str = 'EPSG:3857'

MARGEN: float = 1.15


def acercar_a_municipios(canvas: Any, cajas: dict[str, tuple[float, float, float, float]],
                         claves: list[str]) -> bool:
    elegidas = [cajas[clave] for clave in claves if clave in cajas] or list(cajas.values())
    if canvas is None or not elegidas:
        return False
    caja = QgsRectangle(min(c[0] for c in elegidas), min(c[1] for c in elegidas),
                        max(c[2] for c in elegidas), max(c[3] for c in elegidas))
    transformacion = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem(CRS_CAJAS), canvas.mapSettings().destinationCrs(),
        QgsProject.instance())
    destino = transformacion.transformBoundingBox(caja)
    destino.scale(MARGEN)
    canvas.setExtent(destino)
    canvas.refresh()
    return True
