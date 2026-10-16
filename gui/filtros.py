from typing import Any, Callable, Optional

from qgis.gui import QgsCheckableComboBox
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QComboBox, QGridLayout, QLabel, QPushButton, QWidget

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
from ..tasks import Coordinador, PeriodicidadTask
from ..theme import set_role

AYUDA_MUNICIPIO: str = ('Filtra la capa por municipio. Aplica al mapa, a la consulta por clic '
                        'y a la descarga.')

AYUDA_FECHA: str = ('Periodo que se dibuja. Arranca en el mismo que usa el visor; «Todas» '
                    'quita el filtro y encima todos los periodos.')

CLAVE_TAREA: str = 'periodicidad'

Listo = Callable[[Filtro, Optional[str]], None]


def _ayuda(texto: str) -> QLabel:
    etiqueta = QLabel('?')
    etiqueta.setToolTip(texto)
    etiqueta.setAlignment(Qt.AlignCenter)
    etiqueta.setFixedSize(18, 18)
    set_role(etiqueta, 'badge')
    return etiqueta


class ControlFiltros:

    def __init__(self, client: MapaLabClient, tareas: Coordinador,
                 al_cambiar: Callable[[dict[str, Any], Filtro, Optional[str]], None]) -> None:
        self._client = client
        self._tareas = tareas
        self._al_cambiar = al_cambiar
        self._node: Optional[dict[str, Any]] = None
        self._periodos: dict[str, tuple[dict[int, list[int]], Optional[str]]] = {}
        self._esperando: dict[str, list[Listo]] = {}
        self._silencio = False
        self.widget = self._construir()
        self.mostrar(None)

    def _construir(self) -> QWidget:
        caja = QWidget()
        grid = QGridLayout(caja)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(8)

        self._etiqueta_mun = QLabel('Municipio')
        self._municipios = QgsCheckableComboBox()
        self._municipios.setDefaultText('Todos')
        self._municipios.checkedItemsChanged.connect(lambda _: self._cambio())
        self._zmg = QPushButton('ZMG')
        self._zmg.setToolTip('Zona Metropolitana de Guadalajara')
        self._zmg.clicked.connect(self._marcar_zmg)
        set_role(self._zmg, 'secondary')
        self._ayuda_mun = _ayuda(AYUDA_MUNICIPIO)

        self._etiqueta_fecha = QLabel('Fecha')
        self._anio = QComboBox()
        self._anio.currentIndexChanged.connect(self._cambio_anio)
        self._mes = QComboBox()
        self._mes.currentIndexChanged.connect(lambda _: self._cambio())
        self._ayuda_fecha = _ayuda(AYUDA_FECHA)

        grid.addWidget(self._etiqueta_mun, 0, 0)
        grid.addWidget(self._municipios, 0, 1, 1, 2)
        grid.addWidget(self._zmg, 0, 3)
        grid.addWidget(self._ayuda_mun, 0, 4)
        grid.addWidget(self._etiqueta_fecha, 1, 0)
        grid.addWidget(self._anio, 1, 1)
        grid.addWidget(self._mes, 1, 2, 1, 2)
        grid.addWidget(self._ayuda_fecha, 1, 4)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
        return caja

    def _fila_municipio(self, visible: bool) -> None:
        for widget in (self._etiqueta_mun, self._municipios, self._zmg, self._ayuda_mun):
            widget.setVisible(visible)

    def _fila_fecha(self, visible: bool) -> None:
        for widget in (self._etiqueta_fecha, self._anio, self._mes, self._ayuda_fecha):
            widget.setVisible(visible)

    def cargar_municipios(self) -> None:
        self._silencio = True
        self._municipios.clear()
        for municipio in sorted(self._client.municipios, key=lambda m: str(m.get('nombre'))):
            self._municipios.addItemWithCheckState(
                str(municipio.get('nombre') or ''), Qt.Unchecked, str(municipio.get('clave')))
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
            self._municipios.setItemCheckState(indice, Qt.Checked if marcado else Qt.Unchecked)

        disponibles = periodos[0] if periodos else {}
        self._fila_fecha(bool(disponibles))
        self._anio.clear()
        self._anio.addItem('Todas', None)
        for anio in sorted(disponibles, reverse=True):
            self._anio.addItem(str(anio), anio)
        self._anio.setCurrentIndex(max(0, self._anio.findData(filtro.anio)))
        self._llenar_meses(disponibles.get(filtro.anio) or [], filtro.mes)
        self._silencio = False

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
                    indice, Qt.Checked if marcar else Qt.Unchecked)
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
        self._al_cambiar(self._node, self.filtro(), self.columna(self._node))
