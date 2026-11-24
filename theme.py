import os
import re
from functools import lru_cache
from typing import Optional

from qgis.PyQt.QtCore import QEvent, QObject, Qt
from qgis.PyQt.QtGui import QColor, QIcon
from qgis.PyQt.QtWidgets import QGraphicsDropShadowEffect, QWidget

from .config import FONT_SCALE_PX

THEME_FILE: str = 'theme.qss'

ASSETS_DIR: str = 'assets'

REFRESH_ICON: str = 'refrescar.svg'

BRAND_ROLE: str = 'brandRole'

BASE_FONT_RE = re.compile(r'(font-size:\s*)(\d+)(px)')


def _theme_path() -> str:
    return os.path.join(os.path.dirname(__file__), THEME_FILE)


@lru_cache(maxsize=1)
def load_stylesheet() -> str:
    path = _theme_path()
    if not os.path.exists(path):
        return ''
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read()
    except OSError:
        return ''


SHADOW_BLUR: float = 14.0

SHADOW_OFFSET: float = 2.0

SHADOW_ALPHA: int = 90


def sombra(widget: QWidget, blur: float = SHADOW_BLUR,
           offset: float = SHADOW_OFFSET) -> QGraphicsDropShadowEffect:
    efecto = QGraphicsDropShadowEffect(widget)
    efecto.setBlurRadius(blur)
    efecto.setOffset(0, offset)
    efecto.setColor(QColor(0, 0, 0, SHADOW_ALPHA))
    efecto.setEnabled(False)
    widget.setGraphicsEffect(efecto)
    return efecto


class _SombraEnHover(QObject):

    def __init__(self, widget: QWidget) -> None:
        super().__init__(widget)
        self._efecto = sombra(widget)
        widget.installEventFilter(self)

    def eventFilter(self, objeto: QObject, evento) -> bool:
        if evento.type() == QEvent.Type.Enter:
            self._efecto.setEnabled(True)
        elif evento.type() == QEvent.Type.Leave:
            self._efecto.setEnabled(False)
        return False


def sombra_en_hover(widget: QWidget) -> None:
    _SombraEnHover(widget)


def icono_refrescar() -> QIcon:
    ruta = os.path.join(os.path.dirname(__file__), ASSETS_DIR, REFRESH_ICON)
    return QIcon(ruta) if os.path.exists(ruta) else QIcon()


def _escalar_fuentes(stylesheet: str) -> str:
    def subir(coincidencia: re.Match) -> str:
        tamano = int(coincidencia.group(2)) + FONT_SCALE_PX
        return f'{coincidencia.group(1)}{tamano}{coincidencia.group(3)}'

    return BASE_FONT_RE.sub(subir, stylesheet)


def _bloque_de_rol(rol: str) -> str:
    patron = r'\[brandRole="' + re.escape(rol) + r'"\]\s*\{([^}]*)\}'
    encontrado = re.search(patron, load_stylesheet())
    return encontrado.group(1) if encontrado else ''


def _bloque_de_selector(selector: str) -> str:
    patron = re.escape(selector) + r'[^{]*\{([^}]*)\}'
    encontrado = re.search(patron, load_stylesheet())
    return encontrado.group(1) if encontrado else ''


def _color(bloque: str, propiedad: str, respaldo: str) -> str:
    patron = r'(?:^|[;{\s])' + re.escape(propiedad) + r'\s*:\s*([^;]+);'
    valor = re.search(patron, bloque)
    return valor.group(1).strip() if valor else respaldo


@lru_cache(maxsize=None)
def color_de_selector(selector: str, propiedad: str, respaldo: str) -> str:
    return _color(_bloque_de_selector(selector), propiedad, respaldo)


@lru_cache(maxsize=None)
def color_de_rol(rol: str, propiedad: str, respaldo: str) -> str:
    return _color(_bloque_de_rol(rol), propiedad, respaldo)


FLECHA_ICON: str = 'flecha.svg'

FONDO_TARJETA: str = '#F3F4F5'


def _ruta_asset(archivo: str) -> str:
    return os.path.join(os.path.dirname(__file__), ASSETS_DIR, archivo).replace('\\', '/')


def _reglas_combo() -> str:
    fondo = color_de_rol('search', 'background-color', '#EAEFFA')
    tinta = color_de_rol('search', 'color', '#5C2472')
    acento = color_de_rol('primary', 'background-color', '#5C2472')
    realce = color_de_selector('QTreeView::item:selected', 'background-color', '#FFE9CC')
    realce_tinta = color_de_selector('QTreeView::item:selected', 'color', '#A85700')
    return (
        f'QComboBox {{ background-color: {fondo}; color: {tinta}; border: 1px solid {fondo};'
        ' border-radius: 16px; padding: 6px 12px; combobox-popup: 0; }\n'
        f'QComboBox:hover, QComboBox:focus, QComboBox:on {{ border: 1px solid {acento}; }}\n'
        'QComboBox:disabled { color: palette(disabled-text); }\n'
        'QComboBox::drop-down { border: none; width: 28px;'
        ' subcontrol-origin: padding; subcontrol-position: center right; }\n'
        f'QComboBox::down-arrow {{ image: url("{_ruta_asset(FLECHA_ICON)}");'
        ' width: 12px; height: 12px; }\n'
        f'QComboBox QAbstractItemView {{ background-color: #FFFFFF; color: {tinta};'
        f' border: 1px solid {fondo}; border-radius: 8px; padding: 4px; outline: none;'
        f' selection-background-color: {realce}; selection-color: {realce_tinta}; }}\n'
        'QComboBox QAbstractItemView::item { padding: 6px 8px; min-height: 22px; }\n'
    )


def _reglas_en_mapa() -> str:
    tinta = color_de_rol('search', 'color', '#5C2472')
    gris = color_de_rol('quiet', 'color', '#465055')
    radio = _color(_bloque_de_rol('search'), 'border-radius', '16px')
    tarjeta = f'background-color: {FONDO_TARJETA}; border: none; border-radius: {radio};'
    quitar = f'color: {gris}; border: none; background: transparent; font-size: 13px;'
    return (
        f'QWidget[brandRole="mapa-tarjeta"] {{ {tarjeta} }}\n'
        f'QWidget[brandRole="mapa-fondo"] {{ {tarjeta} }}\n'
        'QWidget[brandRole="mapa-lista"] { background: transparent; border: none; }\n'
        f'QLabel[brandRole="mapa-contador"] {{ background-color: {tinta}; color: #FFFFFF;'
        ' border-radius: 9px; padding: 0px 7px; font-size: 12px; font-weight: 700;'
        ' min-height: 18px; max-height: 18px; }\n'
        f'QLabel[brandRole="mapa-titulo"] {{ color: {tinta}; font-size: 13px;'
        ' font-weight: 700; padding: 0px 4px; border: none; background: transparent; }\n'
        f'QPushButton[brandRole="mapa-capa"] {{ text-align: left; color: {gris}; border: none;'
        ' background: transparent; padding: 4px 6px; font-size: 14px; }\n'
        f'QPushButton[brandRole="mapa-capa"]:hover {{ color: {tinta}; background-color: #FFFFFF;'
        ' border-radius: 8px; }\n'
        f'QPushButton[brandRole="mapa-quitar"] {{ {quitar} padding: 2px 6px; }}\n'
        f'QPushButton[brandRole="mapa-quitar-fuera"] {{ {quitar} padding: 0px; }}\n'
        'QPushButton[brandRole="mapa-quitar"]:hover,'
        f' QPushButton[brandRole="mapa-quitar-fuera"]:hover {{ color: {tinta}; }}\n'
    )


def _reglas_locales() -> str:
    return (
        '\nQTreeView::branch, QTreeWidget::branch {\n'
        '    image: none;\n'
        '}\n'
        'QPushButton[brandRole="quiet"] { text-align: center; }\n'
    ) + _reglas_combo() + _reglas_en_mapa()


def build_stylesheet() -> str:
    stylesheet = load_stylesheet()
    if not stylesheet:
        return ''
    return _escalar_fuentes(stylesheet) + _reglas_locales()


def apply_theme(widget: QWidget) -> bool:
    stylesheet = build_stylesheet()
    if not stylesheet:
        return False
    widget.setStyleSheet(stylesheet)
    return True


def set_role(widget: QWidget, role: Optional[str]) -> None:
    widget.setProperty(BRAND_ROLE, role)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    style = widget.style()
    if style is not None:
        style.unpolish(widget)
        style.polish(widget)
