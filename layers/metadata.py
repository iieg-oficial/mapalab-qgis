from typing import Any, Optional

from qgis.core import QgsAbstractMetadataBase, QgsLayerMetadata, QgsMapLayer

from ..model.tree import clean_label


def _first_record(payload: Any) -> Optional[dict[str, Any]]:
    if isinstance(payload, list) and payload:
        return payload[0] if isinstance(payload[0], dict) else None
    if isinstance(payload, dict):
        return payload
    return None


def _texto(valor: Any) -> str:
    return valor.strip() if isinstance(valor, str) else ''


def _items(record: dict[str, Any], clave: str) -> list[dict[str, Any]]:
    valor = record.get(clave)
    if not isinstance(valor, list):
        return []
    return [item for item in valor if isinstance(item, dict)]


def _unicos(valores: list[str]) -> list[str]:
    vistos: list[str] = []
    for valor in valores:
        if valor and valor not in vistos:
            vistos.append(valor)
    return vistos


def collect_sources(record: dict[str, Any]) -> list[str]:
    fuentes = [_texto(item.get('largo')) or _texto(item.get('corto'))
               for item in _items(record, 'fuentes')]
    fuentes.append(_texto(record.get('fuentes_texto_largo'))
                   or _texto(record.get('fuentes_texto_corto')))
    return _unicos(fuentes)


def build_abstract(record: dict[str, Any]) -> str:
    metodologias = [_texto(item.get('texto')) for item in _items(record, 'metodologia')]
    metodologias.append(_texto(record.get('metodologia_texto')))
    partes = [_texto(record.get('descripcion')), *_unicos(metodologias),
              _texto(record.get('texto_leyenda_juridico'))]
    return '\n\n'.join(parte for parte in partes if parte)


def _enlace(nombre: str, url: str) -> QgsAbstractMetadataBase.Link:
    entry = QgsAbstractMetadataBase.Link()
    entry.name = nombre
    entry.type = 'WWW:LINK'
    entry.url = url
    return entry


def collect_links(record: dict[str, Any]) -> list[tuple[str, str]]:
    enlaces: list[tuple[str, str]] = [('MapaLab', _texto(record.get('link_final_capa')))]
    for item in _items(record, 'fuentes'):
        nombre = _texto(item.get('enlace_label')) or _texto(item.get('corto')) or 'Fuente'
        enlaces.append((nombre, _texto(item.get('enlace'))))
    enlaces.append(('Fuente', _texto(record.get('fuentes_enlace'))))
    for item in _items(record, 'metodologia'):
        enlaces.append(('Metodología', _texto(item.get('archivo_enlace'))))
    enlaces.append(('Metodología', _texto(record.get('metodologia_archivo_enlace'))))
    for item in _items(record, 'metadato'):
        enlaces.append((_texto(item.get('nombre')) or 'Metadato', _texto(item.get('enlace'))))

    unicos: list[tuple[str, str]] = []
    vistas: set[str] = set()
    for nombre, url in enlaces:
        if url and url not in vistas:
            vistas.add(url)
            unicos.append((nombre, url))
    return unicos


def apply_metadata(layer: QgsMapLayer, payload: Any, node: dict[str, Any]) -> bool:
    record = _first_record(payload)
    if record is None:
        return False

    metadata = QgsLayerMetadata()
    titulo = clean_label(str(node.get('label') or '')) or _texto(record.get('nombre_capa_usuario'))
    metadata.setTitle(titulo)

    abstract = build_abstract(record)
    if abstract:
        metadata.setAbstract(abstract)

    sources = collect_sources(record)
    if sources:
        metadata.setRights(sources)

    palabras = {
        'tema': _texto(record.get('tema')),
        'frecuencia': _texto(record.get('frecuencia_actualizacion')),
        'actualizacion': _texto(record.get('fecha_ultima_actualizacion')),
    }
    for vocabulario, valor in palabras.items():
        if valor:
            metadata.addKeywords(vocabulario, [valor])

    for nombre, url in collect_links(record):
        metadata.addLink(_enlace(nombre, url))

    layer.setMetadata(metadata)
    return True
