import hashlib
import os
import tempfile
import time
from typing import Optional

from qgis.core import QgsApplication

from .config import get_base_url

RAIZ: str = 'mapalab'


def carpeta(*partes: str) -> str:
    path = os.path.join(QgsApplication.qgisSettingsDirPath(), RAIZ, *partes)
    os.makedirs(path, exist_ok=True)
    return path


def carpeta_del_servidor(*partes: str) -> str:
    huella = hashlib.sha1(get_base_url().encode('utf-8')).hexdigest()[:12]
    return carpeta('servidores', huella, *partes)


def leer(path: str) -> Optional[bytes]:
    try:
        with open(path, 'rb') as handle:
            return handle.read()
    except OSError:
        return None


def escribir_atomico(path: str, datos: bytes) -> bool:
    directorio = os.path.dirname(path) or '.'
    try:
        descriptor, temporal = tempfile.mkstemp(prefix='.', suffix='.part', dir=directorio)
    except OSError:
        return False
    try:
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(datos)
        os.replace(temporal, path)
        return True
    except OSError:
        try:
            os.remove(temporal)
        except OSError:
            pass
        return False


def edad_s(path: str) -> Optional[float]:
    try:
        return max(0.0, time.time() - os.path.getmtime(path))
    except OSError:
        return None
