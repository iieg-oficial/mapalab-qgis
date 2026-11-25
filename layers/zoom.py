from typing import Any

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
)

CRS_CAJAS: str = 'EPSG:3857'

MARGEN: float = 1.15


def ajustar_a(canvas: Any, extension: QgsRectangle, ocupado: int = 0) -> bool:
    if extension.isNull() or extension.isEmpty():
        return False
    ancho, alto = canvas.width(), canvas.height()
    libre = max(1, ancho - ocupado)
    escala = max(extension.width() / libre, extension.height() / max(1, alto))
    centro = extension.center()
    x = centro.x() + ocupado / 2 * escala
    canvas.setExtent(QgsRectangle(x - ancho / 2 * escala, centro.y() - alto / 2 * escala,
                                  x + ancho / 2 * escala, centro.y() + alto / 2 * escala))
    canvas.refresh()
    return True


def acercar_a_municipios(canvas: Any, cajas: dict[str, tuple[float, float, float, float]],
                         claves: list[str], ocupado: int = 0) -> bool:
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
    return ajustar_a(canvas, destino, ocupado)
