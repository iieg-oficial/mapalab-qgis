import os
import re
from functools import lru_cache
from typing import Optional

from qgis.PyQt.QtCore import QEvent, QObject, QSize, Qt
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


def sombra(widget: QWidget, blur: float = SHADOW_BLUR, offset: float = SHADOW_OFFSET,
           color: Optional[QColor] = None) -> QGraphicsDropShadowEffect:
    efecto = QGraphicsDropShadowEffect(widget)
    efecto.setBlurRadius(blur)
    efecto.setOffset(0, offset)
    efecto.setColor(color or QColor(0, 0, 0, SHADOW_ALPHA))
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


def icono_asset(normal: str, hover: Optional[str] = None) -> QIcon:
    carpeta = os.path.join(os.path.dirname(__file__), ASSETS_DIR)
    icono = QIcon(os.path.join(carpeta, normal))
    if hover:
        icono.addFile(os.path.join(carpeta, hover), QSize(), QIcon.Mode.Active)
    return icono


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

FONDO_TARJETA: str = '#FFFFFF'


def _ruta_asset(archivo: str) -> str:
    return os.path.join(os.path.dirname(__file__), ASSETS_DIR, archivo).replace('\\', '/')


def _reglas_combo() -> str:
    fondo = color_de_rol('search', 'background-color', '#EAEFFA')
    tinta = color_de_rol('search', 'color', '#5C2472')
    acento = color_de_rol('primary', 'background-color', '#5C2472')
    realce = color_de_selector('QTreeView::item:selected', 'background-color', '#FFE9CC')
    realce_tinta = color_de_selector('QTreeView::item:selected', 'color', '#A85700')
    gris = color_de_rol('quiet', 'color', '#465055')
    return (
        f'QComboBox {{ background-color: {fondo}; color: {tinta}; border: 1px solid {fondo};'
        ' border-radius: 16px; padding: 11px 12px; combobox-popup: 0; }\n'
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
        f'QMenu {{ background-color: #FFFFFF; color: {gris}; border: 1px solid {fondo};'
        ' border-radius: 8px; padding: 4px; menu-scrollable: 1; }\n'
        'QMenu::item { padding: 7px 24px 7px 12px; margin: 1px 0px; border-radius: 4px;'
        ' background: transparent; }\n'
        'QMenu::item:selected { background-color: rgba(70, 80, 85, 20); }\n'
        f'QMenu::item:checked {{ background-color: {realce}; color: {realce_tinta}; }}\n'
        'QMenu::indicator { width: 0px; height: 0px; }\n'
        f'QMenu::separator {{ height: 1px; background: {fondo}; margin: 4px 6px; }}\n'
    )


def _reglas_en_mapa() -> str:
    tinta = color_de_rol('search', 'color', '#5C2472')
    gris = color_de_rol('quiet', 'color', '#465055')
    fondo = color_de_rol('search', 'background-color', '#EAEFFA')
    radio = _color(_bloque_de_rol('search'), 'border-radius', '16px')
    tarjeta = f'background-color: {FONDO_TARJETA}; border: none; border-radius: {radio};'
    return (
        f'QWidget[brandRole="mapa-tarjeta"] {{ {tarjeta} }}\n'
        'QWidget[brandRole="mapa-lista"] { background: transparent; border: none; }\n'
        f'QLabel[brandRole="mapa-contador"] {{ background-color: {tinta}; color: #FFFFFF;'
        ' border-radius: 9px; padding: 0px; font-size: 11px; font-weight: 700; }\n'
        f'QLabel[brandRole="mapa-titulo"] {{ color: {tinta}; font-size: 15px;'
        ' font-weight: 700; padding: 0px 2px; border: none; background: transparent; }\n'
        'QLabel[brandRole="mapa-titulo-capas"] { color: #000000; font-size: 15px;'
        ' font-weight: 700; padding: 0px 2px; border: none; background: transparent; }\n'
        f'QPushButton[brandRole="mapa-capa"] {{ text-align: left; color: {gris}; border: none;'
        ' background: transparent; padding: 4px 6px; font-size: 16px; }\n'
        f'QPushButton[brandRole="mapa-capa"]:hover {{ color: {tinta}; background-color: {fondo};'
        ' border-radius: 8px; }\n'
        f'QToolButton[brandRole="mapa-icono"] {{ background-color: {FONDO_TARJETA}; border: none;'
        ' border-radius: 24px; padding: 0px; }\n'
        f'QToolButton[brandRole="mapa-icono"]:hover {{ background-color: {fondo}; }}\n'
        f'QPushButton[brandRole="mapa-fecha"] {{ color: {tinta}; background-color: #FFFFFF;'
        f' border: 1px solid {tinta}; border-radius: 12px; padding: 2px 10px;'
        ' font-size: 13px; font-weight: 700; min-height: 18px; }\n'
        'QPushButton[brandRole="mapa-fecha"]::menu-indicator { image: none; width: 0px; }\n'
        f'QPushButton[brandRole="mapa-fecha-lectura"] {{ color: {tinta}; background-color:'
        f' {fondo}; border: none; border-radius: 11px; padding: 2px 9px; font-size: 12px;'
        ' font-weight: 700; }\n'
        f'QPushButton[brandRole="mapa-fecha-lectura"]:hover {{ border: 1px solid {tinta}; }}\n'
        'QToolButton[brandRole="mapa-accion"] { border: none; background: transparent;'
        ' padding: 2px; border-radius: 6px; }\n'
        'QToolButton[brandRole="mapa-accion"]:hover { background-color: rgba(92, 36, 114, 20); }\n'
        'QToolButton[brandRole="mapa-accion"]::menu-indicator { image: none; width: 0px; }\n'
        f'QListWidget[brandRole="compartido-lista"] {{ background-color: #FFFFFF; color: {gris};'
        ' border: none; border-radius: 13px; padding: 6px; }\n'
        'QListWidget[brandRole="compartido-lista"]::item { padding: 4px 6px; }\n'
        f'QCheckBox {{ color: {gris}; }}\n'
        'QWidget[brandRole="mapa-aviso"] { background-color: #FFFFFF; border: none;'
        ' border-radius: 16px; }\n'
        f'QLabel[brandRole="mapa-aviso-texto"] {{ color: {gris}; background: transparent;'
        ' border: none; font-size: 14px; }\n'
        'QToolButton[brandRole="borde-scroll"] { background-color: #FFFFFF;'
        ' border: 1px solid transparent; border-radius: 11px; }\n'
        f'QToolButton[brandRole="borde-scroll"]:hover {{ border: 1px solid {tinta}; }}\n'
        'QPushButton[brandRole="mapa-fecha"]:hover { background-color: #F7F0FA; }\n'
        f'QPushButton[brandRole="mapa-capa-activa"] {{ text-align: left; color: {tinta};'
        ' border: none; background: transparent; padding: 4px 6px;'
        ' font-size: 16px; font-weight: 700; }\n'
        f'QLabel[brandRole="mapa-asa"] {{ color: {gris}; background: transparent; border: none;'
        ' font-size: 15px; padding: 0px 2px; }\n'
        f'QLabel[brandRole="mapa-asa"]:hover {{ color: {tinta}; }}\n'
        f'QFrame[brandRole="mapa-guia"] {{ background-color: {tinta}; border: none;'
        ' border-radius: 1px; }\n'
        'QWidget[brandRole="mapa-leyenda"] { background-color: #FFFFFF; border: none;'
        ' border-radius: 13px; }\n'
        f'QWidget[brandRole="mapa-item-abierto"] {{ background-color: {fondo}; border: none;'
        ' border-radius: 13px; }\n'
        f'QLabel[brandRole="mapa-leyenda-texto"] {{ color: {gris}; background: transparent;'
        ' border: none; font-size: 14px; }\n'
        f'QLabel[brandRole="mapa-leyenda-subtitulo"] {{ color: {tinta}; background: transparent;'
        ' border: none; font-size: 14px; font-weight: 700; }\n'
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
