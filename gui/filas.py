from typing import Any

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QToolButton, QWidget

from ..theme import icono_asset, set_role
from .lista_mapa import boton_accion

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


AYUDA_COMPARTIDO: str = ('Abre un mapa compartido desde el visor: pega su enlace (…/mapa?s=…) y '
                         'trae sus capas, filtros, vista y anotaciones.')

def boton_compartido(al_abrir: Any) -> QToolButton:
    return boton_accion(icono_asset('compartido.svg'),
                        AYUDA_COMPARTIDO, al_abrir)


def acciones_titulo(*botones: QWidget) -> QWidget:
    caja = QWidget()
    layout = QHBoxLayout(caja)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    for boton in botones:
        layout.addWidget(boton, 0, Qt.AlignmentFlag.AlignVCenter)
    return caja
