from typing import Any

from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from ..theme import set_role, sombra_en_hover

PLACEHOLDER: str = 'https://dominio-del-iieg'


def fila_servidor(al_guardar: Any) -> tuple[QWidget, QLineEdit]:
    fila = QWidget()
    layout = QHBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)

    entrada = QLineEdit()
    entrada.setPlaceholderText(PLACEHOLDER)
    boton = QPushButton('Guardar')
    boton.clicked.connect(al_guardar)

    layout.addWidget(QLabel('Servidor:'))
    layout.addWidget(entrada)
    layout.addWidget(boton)
    fila.setLayout(layout)

    set_role(fila, 'card')
    set_role(boton, 'primary')
    return fila, entrada


AYUDA_AGREGAR: str = ('Agrega al mapa la capa elegida en el árbol como WMS, con el municipio y '
                     'la fecha que marque el panel. Si eliges un grupo, trae todas sus capas.')

AYUDA_DESCARGAR: str = ('Descarga la capa vectorial elegida como GeoPackage en tu equipo, ya '
                        'filtrada por municipio y fecha, para editarla o analizarla sin conexión.')

AYUDA_LIMPIAR: str = ('Quita del proyecto las capas «Selección — …» que deja la consulta por '
                      'clic sobre el mapa.')

AYUDA_ABRIR: str = ('Abre un mapa compartido desde el visor: pega su enlace (…/mapa?s=…) y trae '
                    'sus capas, filtros, vista y anotaciones.')


PESO_PRINCIPAL: int = 3

PESO_SECUNDARIO: int = 2


def _boton(texto: str, ayuda: str, al_pulsar: Any, rol: str) -> QPushButton:
    boton = QPushButton(texto)
    boton.setToolTip(ayuda)
    boton.clicked.connect(al_pulsar)
    set_role(boton, rol)
    return boton


def fila_acciones(al_agregar: Any, al_descargar: Any, al_limpiar: Any,
                  al_abrir: Any) -> tuple[QHBoxLayout, QPushButton]:
    agregar = _boton('Agregar', AYUDA_AGREGAR, al_agregar, 'primary')
    sombra_en_hover(agregar)

    fila = QHBoxLayout()
    fila.setSpacing(6)
    fila.addWidget(agregar, PESO_PRINCIPAL)
    fila.addWidget(_boton('Descargar', AYUDA_DESCARGAR, al_descargar, 'secondary'), PESO_PRINCIPAL)
    fila.addWidget(_boton('Limpiar', AYUDA_LIMPIAR, al_limpiar, 'quiet'), PESO_SECUNDARIO)
    fila.addWidget(_boton('Abrir', AYUDA_ABRIR, al_abrir, 'quiet'), PESO_SECUNDARIO)
    return fila, agregar
