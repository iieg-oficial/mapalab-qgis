from typing import Optional

from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtWidgets import QHBoxLayout, QPushButton, QWidget

from ..config import MODO_IIEG, MODO_INEGI
from ..theme import color_de_rol, set_role

ALTO: int = 30

RADIO: int = ALTO // 2

RELLENO: int = 2

APAGADO: str = '#9AA7B8'

ETIQUETAS: tuple[tuple[str, str], ...] = ((MODO_IIEG, 'IIEG'), (MODO_INEGI, 'INEGI'))


def _reglas() -> str:
    tinta = color_de_rol('search', 'color', '#5C2472')
    superficie = color_de_rol('search', 'background-color', '#EAEFFA')

    return (
        'QWidget[brandRole="switch"] { background-color: #FFFFFF;'
        f' border-radius: {RADIO}px; }}\n'
        'QWidget[brandRole="switch"] QPushButton { background-color: transparent;'
        f' color: {APAGADO}; border: none; border-radius: {RADIO - RELLENO}px;'
        ' padding: 0px 8px; font-size: 12px; font-weight: 700; }\n'
        f'QWidget[brandRole="switch"] QPushButton:hover {{ color: {tinta}; }}\n'
        'QWidget[brandRole="switch"] QPushButton:checked {'
        f' background-color: {superficie}; color: {tinta}; }}\n'
        'QWidget[brandRole="switch"] QPushButton:disabled { color: palette(disabled-text); }\n'
    )


def _tooltip(etiqueta: str, activo: bool, hay_modo: bool) -> str:
    if activo:
        return f'Límites de {etiqueta} en el mapa'
    return f'Cambiar a {etiqueta}' if hay_modo else f'Activar capas {etiqueta}'


class SwitchModoBase(QWidget):

    cambiado = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._modo: Optional[str] = None
        self._botones: dict[str, QPushButton] = {}

        layout = QHBoxLayout()
        layout.setContentsMargins(RELLENO, RELLENO, RELLENO, RELLENO)
        layout.setSpacing(2)

        for indice, (modo, etiqueta) in enumerate(ETIQUETAS):
            boton = QPushButton(etiqueta)
            boton.setCheckable(True)
            boton.setFixedHeight(ALTO - 2 * RELLENO)
            boton.setCursor(Qt.CursorShape.PointingHandCursor)
            boton.setProperty('modo', modo)
            boton.clicked.connect(lambda _, elegido=modo: self._al_pulsar(elegido))
            layout.addWidget(boton)
            self._botones[modo] = boton

        self.setLayout(layout)
        self.setFixedHeight(ALTO)
        set_role(self, 'switch')
        self.setStyleSheet(_reglas())
        self.mostrar(None)

    def modo(self) -> Optional[str]:
        return self._modo

    def mostrar(self, modo: Optional[str]) -> None:
        self._modo = modo
        for clave, etiqueta in ETIQUETAS:
            boton = self._botones[clave]
            activo = clave == modo
            boton.setChecked(activo)
            boton.setToolTip(_tooltip(etiqueta, activo, modo is not None))

    def _al_pulsar(self, modo: str) -> None:
        if modo == self._modo:
            self._botones[modo].setChecked(True)
            return
        self.cambiado.emit(modo)
