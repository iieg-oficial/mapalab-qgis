from typing import Any, Callable, Optional

from qgis.core import QgsTask
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..api.client import MapaLabCancelado, MapaLabClient, MapaLabError
from ..layers.compartido import (
    MAPA_BASE,
    MAPAS_BASE_DEL_VISOR,
    Plan,
    codigo_de,
    construir,
    encuadrar,
    planear,
)
from ..layers.filtros import (
    Filtro,
    anios_y_meses,
    columna_de,
    combinar,
    cql_fecha,
    es_raster_tiempo,
    fecha_por_defecto,
    periodicidad_raster,
    sufijo,
    valor_time,
)
from ..tasks import Coordinador, _TareaMapaLab
from ..theme import apply_theme, set_role

CLAVE_TAREA: str = 'compartido'

MODOS: dict[str, str] = {'iieg': 'límites IIEG', 'inegi': 'límites INEGI'}


class CompartidoTask(_TareaMapaLab):

    listo = pyqtSignal(object)
    fallo = pyqtSignal(str)

    def __init__(self, client: MapaLabClient, codigo: str, arbol: list[dict[str, Any]]) -> None:
        super().__init__('MapaLab: mapa compartido', QgsTask.CanCancel | QgsTask.Silent)
        self._client = client
        self._codigo = codigo
        self._arbol = arbol
        self._plan: Optional[Plan] = None

    def _fechas(self, plan: Plan) -> None:
        for capa in plan.capas:
            if self.isCanceled():
                return
            if es_raster_tiempo(capa.node) and not capa.time_value:
                anio, mes = fecha_por_defecto(
                    capa.node, anios_y_meses(periodicidad_raster(capa.node)))
                capa.time_value = valor_time(capa.node, anio, mes)
                continue
            if not capa.falta_fecha:
                continue
            wms_config = capa.node.get('wmsConfig') or {}
            try:
                periodicidad, columna = self._client.fetch_periodicity(
                    wms_config.get('geoserverWorkspace') or '',
                    wms_config.get('geoserverLayer') or '', feedback=self._feedback)
            except MapaLabError:
                periodicidad, columna = {}, None
            anio, mes = fecha_por_defecto(capa.node, anios_y_meses(periodicidad))
            capa.fecha = cql_fecha(columna_de(capa.node, columna), anio, mes)
            capa.cql = combinar(capa.cql, capa.fecha)
            capa.falta_fecha = False
            capa.nota = ' · '.join(p for p in (sufijo(Filtro([], anio, mes), []),
                                                '' if capa.visible else 'oculta') if p)

    def run(self) -> bool:
        try:
            sobre = self._client.fetch_share(self._codigo, feedback=self._feedback)
            self._plan = planear(self._codigo, sobre, self._arbol)
            self._fechas(self._plan)
        except MapaLabCancelado:
            return False
        except MapaLabError as exc:
            texto = str(exc)
            self._error = ('Ese mapa compartido no existe o expiró.'
                           if ' 404' in texto else texto)
            return False
        return not self.isCanceled()

    def finished(self, result: bool) -> None:
        if result and self._plan is not None:
            self.listo.emit(self._plan)
        elif not self.isCanceled():
            self.fallo.emit(self._error or 'No se pudo leer el mapa compartido.')


class DialogoCompartido(QDialog):

    def __init__(self, client: MapaLabClient, tareas: Coordinador,
                 arbol: Callable[[], list[dict[str, Any]]], canvas: Any,
                 al_terminar: Callable[[str], None], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Abrir mapa compartido')
        self.setMinimumWidth(460)
        self._client = client
        self._tareas = tareas
        self._arbol = arbol
        self._canvas = canvas
        self._al_terminar = al_terminar
        self._plan: Optional[Plan] = None
        self._construir()
        set_role(self, 'panel')
        apply_theme(self)

    def _construir(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Enlace o código'))
        fila = QHBoxLayout()
        self._entrada = QLineEdit()
        self._entrada.setPlaceholderText('https://…/mapalab/mapa?s=…')
        self._entrada.returnPressed.connect(self._ver)
        ver = QPushButton('Ver')
        ver.clicked.connect(self._ver)
        set_role(ver, 'secondary')
        fila.addWidget(self._entrada)
        fila.addWidget(ver)
        layout.addLayout(fila)

        self._resumen = QLabel('')
        self._resumen.setWordWrap(True)
        layout.addWidget(self._resumen)
        self._lista = QListWidget()
        self._lista.setVisible(False)
        layout.addWidget(self._lista)
        self._base = QCheckBox('')
        self._notas = QCheckBox('')
        for casilla in (self._base, self._notas):
            casilla.setChecked(True)
            casilla.setVisible(False)
            layout.addWidget(casilla)

        botones = QHBoxLayout()
        botones.addStretch(1)
        self._agregar = QPushButton('Agregar al proyecto')
        self._agregar.setEnabled(False)
        self._agregar.clicked.connect(self._construir_plan)
        set_role(self._agregar, 'primary')
        cancelar = QPushButton('Cancelar')
        cancelar.clicked.connect(self.reject)
        set_role(cancelar, 'quiet')
        botones.addWidget(self._agregar)
        botones.addWidget(cancelar)
        layout.addLayout(botones)

    def _ver(self) -> None:
        codigo = codigo_de(self._entrada.text())
        if not codigo:
            self._resumen.setText('Pega el enlace del visor (…/mapa?s=…) o su código de 10 letras.')
            return
        if not self._arbol():
            self._resumen.setText('El catálogo aún no carga.')
            return
        self._agregar.setEnabled(False)
        self._resumen.setText('Leyendo el mapa compartido…')
        self._tareas.cancelar(CLAVE_TAREA)
        self._tareas.lanzar(CLAVE_TAREA, CompartidoTask(self._client, codigo, self._arbol()),
                            self._mostrar, self._resumen.setText)

    def _mostrar(self, plan: Plan) -> None:
        self._plan = plan
        partes = [f'{len(plan.capas)} capas']
        if plan.modo:
            partes.append(MODOS[plan.modo])
        if plan.municipios:
            partes.append(f'{len(plan.municipios)} municipio(s)')
        self._resumen.setText(' · '.join(partes))

        self._lista.clear()
        for capa in plan.capas:
            marca = '◉' if capa.visible else '○'
            nota = f'   {capa.nota}' if capa.nota else ''
            self._lista.addItem(f'{marca}  {capa.etiqueta()}{nota}')
        for faltante in plan.faltantes:
            self._lista.addItem(f'⚠  {faltante}   ya no está en el catálogo')
        self._lista.setVisible(True)

        self._base.setText(f'Mapa base {MAPA_BASE[0]}')
        self._base.setVisible(plan.mapa_base in MAPAS_BASE_DEL_VISOR)
        self._notas.setText(f'Anotaciones ({len(plan.anotaciones)})')
        self._notas.setVisible(bool(plan.anotaciones))
        self._agregar.setEnabled(bool(plan.capas))

    def _construir_plan(self) -> None:
        if self._plan is None:
            return
        agregadas, fallidas = construir(
            self._plan, self._client.municipios,
            not self._base.isHidden() and self._base.isChecked(),
            not self._notas.isHidden() and self._notas.isChecked())
        if self._canvas is not None:
            encuadrar(self._canvas, self._plan.vista)
        mensaje = f'Mapa compartido {self._plan.codigo}: {agregadas} capas.'
        if fallidas:
            mensaje += ' No entraron: ' + ', '.join(fallidas) + '.'
        self._al_terminar(mensaje)
        self.accept()
