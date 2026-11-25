from typing import Any, Callable, Optional

from qgis.gui import QgsCheckableComboBox
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QComboBox, QGridLayout, QPushButton, QSizePolicy, QWidget

from ..api.client import MapaLabClient
from ..layers.filtros import (
    MESES,
    ZMG,
    Filtro,
    anios_y_meses,
    campo_municipio,
    es_raster_tiempo,
    Parametros,
    fecha_por_defecto,
    filtro_de_capa,
    parametros,
    periodicidad_raster,
)
from ..layers.grupos import es_grupo, hojas_de
from ..layers.proyecto import capa_por_nodo
from ..periodicidad import PeriodicidadTask
from .menu_combo import como_menu
from .pildora_fecha import etiqueta
from ..tasks import Coordinador
from ..theme import set_role

AYUDA_MUNICIPIO: str = ('Municipio: filtra la capa elegida y acerca el mapa a lo marcado. Sin '
                        'marcar ninguno se ve todo Jalisco; marca uno o varios para ver solo '
                        'esos. El filtro se aplica al mapa, a la consulta por clic y a la '
                        'descarga en GeoPackage.')

AYUDA_ZMG: str = ('Marca de un clic los municipios de la Zona Metropolitana de Guadalajara. '
                  'Otro clic los desmarca.')

AYUDA_ANIO: str = ('Año que se dibuja. Arranca en el mismo periodo que usa el visor; «Todas» '
                   'quita el filtro y dibuja todos los periodos encimados. Se aplica al mapa, a '
                   'la consulta por clic y a la descarga.')

AYUDA_MES: str = 'Mes del año elegido; «Todo el año» junta los doce meses.'

TEXTO_TODOS: str = 'Jalisco'

VISIBLES: int = 12

CLAVE_TAREA: str = 'periodicidad'

Listo = Callable[[Filtro, Optional[str]], None]


class ControlFiltros:

    def __init__(self, client: MapaLabClient, tareas: Coordinador,
                 al_cambiar: Callable[[dict[str, Any], Filtro, Optional[str]], None],
                 al_acercar: Optional[Callable[[list[str]], Any]] = None) -> None:
        self._client = client
        self._tareas = tareas
        self._al_cambiar = al_cambiar
        self._al_acercar = al_acercar
        self._ultimos: list[str] = []
        self._node: Optional[dict[str, Any]] = None
        self._periodos: dict[str, tuple[dict[int, list[int]], Optional[str]]] = {}
        self._esperando: dict[str, list[Listo]] = {}
        self._silencio = False
        self._con_fecha = False
        self.al_mostrar: Optional[Callable[[], None]] = None
        self.widget = self._construir()
        self.mostrar(None)

    def _construir(self) -> QWidget:
        caja = QWidget()
        caja.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        grid = QGridLayout(caja)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)

        self._municipios = QgsCheckableComboBox()
        self._municipios.setDefaultText(TEXTO_TODOS)
        self._municipios.checkedItemsChanged.connect(lambda _: self._cambio())
        self._zmg = QPushButton('ZMG')
        self._zmg.clicked.connect(self._marcar_zmg)
        self._zmg.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        set_role(self._zmg, 'secondary')

        self._anio = QComboBox()
        self._anio.currentIndexChanged.connect(self._cambio_anio)
        self._mes = QComboBox()
        self._mes.currentIndexChanged.connect(lambda _: self._cambio())

        for widget, ayuda in ((self._municipios, AYUDA_MUNICIPIO), (self._zmg, AYUDA_ZMG),
                              (self._anio, AYUDA_ANIO), (self._mes, AYUDA_MES)):
            widget.setToolTip(ayuda)
        for combo in (self._municipios, self._anio, self._mes):
            combo.setMaxVisibleItems(VISIBLES)
            como_menu(combo)

        grid.addWidget(self._municipios, 0, 0)
        grid.addWidget(self._zmg, 0, 1)
        grid.setColumnStretch(0, 1)
        return caja

    def _fila_municipio(self, visible: bool) -> None:
        for widget in (self._municipios, self._zmg):
            widget.setVisible(visible)

    def _fila_fecha(self, visible: bool) -> None:
        self._con_fecha = visible

    def clave_con_fecha(self) -> Optional[str]:
        return self._clave(self._node) if self._node is not None and self._con_fecha else None

    def periodo_de(self, clave: str) -> Optional[str]:
        capa = capa_por_nodo(clave)
        filtro = filtro_de_capa(capa) if capa is not None else None
        periodos = self._periodos.get(clave)
        if filtro is None or (filtro.anio is None and not (periodos and periodos[0])):
            return None
        return etiqueta(filtro.anio, filtro.mes)

    def periodos_actuales(self) -> dict[int, list[int]]:
        periodos = self._periodos_de(self._node) if self._node is not None else None
        return periodos[0] if periodos else {}

    def fecha_actual(self) -> tuple[Optional[int], Optional[int]]:
        return self._anio.currentData(), self._mes.currentData()

    def elegir_fecha(self, anio: Optional[int], mes: Optional[int]) -> None:
        if self._node is None:
            return
        self._silencio = True
        self._anio.setCurrentIndex(max(0, self._anio.findData(anio)))
        self._llenar_meses(self.periodos_actuales().get(anio) or [], mes)
        self._silencio = False
        self._cambio()

    def _avisar(self) -> None:
        if self.al_mostrar is not None:
            self.al_mostrar()

    def cargar_municipios(self) -> None:
        self._silencio = True
        self._municipios.clear()
        for municipio in sorted(self._client.municipios, key=lambda m: str(m.get('nombre'))):
            self._municipios.addItemWithCheckState(
                str(municipio.get('nombre') or ''), Qt.CheckState.Unchecked,
                str(municipio.get('clave')))
        self._silencio = False

    def olvidar(self) -> None:
        self._periodos.clear()
        self._esperando.clear()

    def _clave(self, node: dict[str, Any]) -> str:
        return str(node.get('id') or '')

    def _periodos_de(self, node: dict[str, Any]) -> Optional[tuple[dict[int, list[int]],
                                                                   Optional[str]]]:
        if es_raster_tiempo(node):
            return anios_y_meses(periodicidad_raster(node)), None
        return self._periodos.get(self._clave(node))

    def _pedir(self, node: dict[str, Any], al_tener: Optional[Listo] = None) -> None:
        clave = self._clave(node)
        if al_tener is not None:
            self._esperando.setdefault(clave, []).append(al_tener)
        tarea_clave = f'{CLAVE_TAREA}:{clave}'
        if self._tareas.ocupado(tarea_clave):
            return

        def listo(periodicidad: dict, columna: str) -> None:
            self._periodos[clave] = (anios_y_meses(periodicidad), columna or None)
            self._resolver(node)

        def fallo(_: str) -> None:
            self._periodos[clave] = ({}, None)
            self._resolver(node)

        self._tareas.lanzar(tarea_clave, PeriodicidadTask(self._client, node), listo, fallo)

    def _resolver(self, node: dict[str, Any]) -> None:
        if self._node is not None and self._clave(self._node) == self._clave(node):
            self.mostrar(node)
        for al_tener in self._esperando.pop(self._clave(node), []):
            al_tener(self._por_defecto(node), self.columna(node))

    def columna(self, node: dict[str, Any]) -> Optional[str]:
        periodos = self._periodos_de(node)
        return periodos[1] if periodos else None

    def _por_defecto(self, node: dict[str, Any]) -> Filtro:
        periodos = self._periodos_de(node)
        anio, mes = fecha_por_defecto(node, periodos[0] if periodos else {})
        return Filtro([], anio, mes)

    def con_filtro(self, node: dict[str, Any], al_tener: Listo) -> None:
        if not node.get('wmsConfig'):
            actual = self._node is not None and self._clave(self._node) == self._clave(node)
            al_tener(Filtro(self.filtro().municipios if actual else []), None)
            return
        if self._node is not None and self._clave(self._node) == self._clave(node):
            if self._periodos_de(node) is not None or not node.get('defaultDate'):
                al_tener(self.filtro(), self.columna(node))
                return
        elif self._periodos_de(node) is not None or not node.get('defaultDate'):
            al_tener(self._por_defecto(node), self.columna(node))
            return
        self._pedir(node, al_tener)

    def mostrar(self, node: Optional[dict[str, Any]]) -> None:
        valido = bool(node) and (bool(node.get('wmsConfig')) or es_grupo(node))
        self._node = node if valido else None
        if self._node is None:
            self._fila_municipio(False)
            self._fila_fecha(False)
            self._avisar()
            return

        capa = capa_por_nodo(self._clave(self._node))
        actual = filtro_de_capa(capa) if capa is not None else None
        hoja = bool(self._node.get('wmsConfig'))
        periodos = self._periodos_de(self._node) if hoja else ({}, None)
        if periodos is None and not es_raster_tiempo(self._node):
            self._pedir(self._node)

        filtro = actual or (self._por_defecto(self._node) if hoja else Filtro())
        self._silencio = True
        campo = any(campo_municipio(h)[0] for h in hojas_de(self._node))
        self._fila_municipio(campo and self._municipios.count() > 0)
        for indice in range(self._municipios.count()):
            marcado = self._municipios.itemData(indice) in filtro.municipios
            estado = Qt.CheckState.Checked if marcado else Qt.CheckState.Unchecked
            self._municipios.setItemCheckState(indice, estado)
        self._ultimos = sorted(filtro.municipios)

        disponibles = periodos[0] if periodos else {}
        self._fila_fecha(bool(disponibles))
        self._anio.clear()
        self._anio.addItem('Todas', None)
        for anio in sorted(disponibles, reverse=True):
            self._anio.addItem(str(anio), anio)
        self._anio.setCurrentIndex(max(0, self._anio.findData(filtro.anio)))
        self._llenar_meses(disponibles.get(filtro.anio) or [], filtro.mes)
        self._silencio = False
        self._avisar()

    def _llenar_meses(self, meses: list[int], elegido: Optional[int]) -> None:
        self._mes.clear()
        self._mes.addItem('Todo el año', None)
        for mes in meses:
            self._mes.addItem(MESES[mes - 1].capitalize(), mes)
        self._mes.setCurrentIndex(max(0, self._mes.findData(elegido)))
        self._mes.setEnabled(self._anio.currentData() is not None)

    def _cambio_anio(self, _: int) -> None:
        if self._silencio or self._node is None:
            return
        periodos = self._periodos_de(self._node)
        disponibles = periodos[0] if periodos else {}
        self._silencio = True
        self._llenar_meses(disponibles.get(self._anio.currentData()) or [], None)
        self._silencio = False
        self._cambio()

    def _marcar_zmg(self) -> None:
        elegidos = set(self._municipios.checkedItemsData())
        marcar = not set(ZMG) <= elegidos
        self._silencio = True
        for indice in range(self._municipios.count()):
            if self._municipios.itemData(indice) in ZMG:
                self._municipios.setItemCheckState(
                    indice, Qt.CheckState.Checked if marcar else Qt.CheckState.Unchecked)
        self._silencio = False
        self._cambio()

    def filtro(self) -> Filtro:
        municipios = ([str(dato) for dato in self._municipios.checkedItemsData()]
                      if not self._municipios.isHidden() else [])
        return Filtro(municipios, self._anio.currentData(), self._mes.currentData())

    def parametros_de(self, node: dict[str, Any]) -> Parametros:
        actual = self._node is not None and self._clave(self._node) == self._clave(node)
        filtro = self.filtro() if actual else self._por_defecto(node)
        return parametros(node, filtro, self._client.municipios, self.columna(node))

    def _cambio(self) -> None:
        if self._silencio or self._node is None:
            return
        filtro = self.filtro()
        self._al_cambiar(self._node, filtro, self.columna(self._node))
        if sorted(filtro.municipios) != self._ultimos and self._al_acercar is not None:
            self._al_acercar(filtro.municipios)
        self._ultimos = sorted(filtro.municipios)
