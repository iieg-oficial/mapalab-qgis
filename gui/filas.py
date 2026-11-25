from typing import Any

from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QPushButton, QToolButton, QWidget

from ..theme import icono_asset, set_role

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

LADO_COMPARTIDO: int = 30


def boton_compartido(al_abrir: Any) -> QToolButton:
    boton = QToolButton()
    boton.setIcon(icono_asset('compartido.svg', 'compartido-hover.svg'))
    boton.setIconSize(QSize(LADO_COMPARTIDO, LADO_COMPARTIDO))
    boton.setAutoRaise(True)
    boton.setToolTip(AYUDA_COMPARTIDO)
    boton.setCursor(Qt.CursorShape.PointingHandCursor)
    boton.clicked.connect(al_abrir)
    set_role(boton, 'mapa-accion')
    return boton


def acciones_titulo(*botones: QWidget) -> QWidget:
    caja = QWidget()
    layout = QHBoxLayout(caja)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    for boton in botones:
        layout.addWidget(boton, 0, Qt.AlignmentFlag.AlignVCenter)
    return caja
