from typing import Any, Callable, Optional

from qgis.PyQt.QtWidgets import QMenu, QPushButton

from ..layers.filtros import MESES
from ..theme import set_role

AYUDA_PILDORA: str = ('Periodo que se dibuja. Arranca en el mismo que usa el visor; se aplica al '
                      'mapa, a la consulta por clic y a la descarga.')

TODAS: str = 'Todas'

TODO_EL_ANIO: str = 'Todo el año'


def etiqueta(anio: Optional[int], mes: Optional[int]) -> str:
    if anio is None:
        return TODAS
    if mes is None:
        return str(anio)
    return f'{MESES[mes - 1][:3].capitalize()} {anio}'


def _accion(menu: QMenu, texto: str, filtros: Any, anio: Optional[int],
            mes: Optional[int], actual: tuple[Optional[int], Optional[int]]) -> None:
    accion = menu.addAction(texto)
    accion.setCheckable(True)
    accion.setChecked((anio, mes) == actual)
    accion.triggered.connect(lambda _=False: filtros.elegir_fecha(anio, mes))


def _menu(filtros: Any, padre: QPushButton) -> QMenu:
    menu = QMenu(padre)
    actual = filtros.fecha_actual()
    _accion(menu, 'Todos los periodos', filtros, None, None, actual)
    menu.addSeparator()
    for anio, meses in sorted(filtros.periodos_actuales().items(), reverse=True):
        if len(meses) <= 1:
            _accion(menu, str(anio), filtros, anio, None, actual)
            continue
        submenu = menu.addMenu(str(anio))
        submenu.menuAction().setCheckable(True)
        submenu.menuAction().setChecked(anio == actual[0])
        _accion(submenu, TODO_EL_ANIO, filtros, anio, None, actual)
        submenu.addSeparator()
        for mes in meses:
            _accion(submenu, MESES[mes - 1].capitalize(), filtros, anio, mes, actual)
    return menu


def pildora_fecha(filtros: Any) -> QPushButton:
    pildora = QPushButton(f'{etiqueta(*filtros.fecha_actual())}  ▾')
    pildora.setToolTip(AYUDA_PILDORA)
    pildora.setMenu(_menu(filtros, pildora))
    set_role(pildora, 'mapa-fecha')
    return pildora


def pildora_lectura(texto: str, al_clic: Callable[[], Any]) -> QPushButton:
    pildora = QPushButton(texto)
    pildora.setToolTip('Periodo que se dibuja. Clic para cambiarlo.')
    pildora.clicked.connect(al_clic)
    set_role(pildora, 'mapa-fecha-lectura')
    return pildora
