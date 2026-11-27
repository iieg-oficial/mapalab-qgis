from typing import Any, Optional

from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from ..theme import icono_asset, set_role
from .arrastre import Arrastre, crear_asa
from .boton_icono import BotonIcono
from .leyenda import Leyendas
from .lista_mapa import (
    ANCHO_TARJETA,
    AYUDA_FILA,
    Fila,
    Nombre,
    accion,
    bote,
    encabezado,
    vaciar,
)
from .pildora_fecha import pildora_fecha, pildora_lectura


class TarjetaEnMapa(QWidget):

    def __init__(self, control: Any, leyendas: Leyendas, filtros: Any, switch: QWidget,
                 parent: QWidget) -> None:
        super().__init__(parent)
        self._control = control
        self._switch = switch
        self._leyendas = leyendas
        self._filtros = filtros
        self.abierta: Optional[str] = None
        self._icono = False
        self._con_leyenda = True
        self._filas: list[Fila] = []
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(12, 10, 8, 10)
        self._layout.setSpacing(2)
        self._arrastre = Arrastre(self, control.mover)
        self.boton = BotonIcono(icono_asset('capas.svg'), 'Capas seleccionadas',
                                self._alternar_icono, parent)
        set_role(self, 'mapa-tarjeta')
        self.setVisible(False)

    def _clic(self, clave: str) -> None:
        if self.abierta == clave:
            self.abierta = None
        else:
            self.abierta = clave
            self._control.elegir(clave)
        self.refrescar(self._filas)

    def _alternar_icono(self) -> None:
        self._icono = not self._icono
        self.refrescar(self._filas)

    def _alternar_leyenda(self) -> None:
        self._con_leyenda = not self._con_leyenda
        self.refrescar(self._filas)

    def _nombre(self, fila: Fila, abierta: bool) -> Nombre:
        nombre = Nombre(fila[1])
        nombre.setToolTip(f'{fila[1]}\n{AYUDA_FILA}')
        nombre.clicked.connect(lambda: self._clic(fila[0]))
        set_role(nombre, 'mapa-capa-activa' if abierta else 'mapa-capa')
        return nombre

    def _renglon(self, fila: Fila, asa: QWidget) -> QHBoxLayout:
        renglon = QHBoxLayout()
        renglon.setContentsMargins(0, 0, 0, 0)
        renglon.setSpacing(4)
        renglon.addWidget(asa)
        renglon.addWidget(self._nombre(fila, False), 1)
        periodo = self._filtros.periodo_de(fila[0])
        if periodo is not None:
            renglon.addWidget(pildora_lectura(periodo, lambda: self._clic(fila[0])))
        return renglon

    def _acciones(self, fila: Fila) -> QHBoxLayout:
        acciones = QHBoxLayout()
        acciones.setContentsMargins(0, 0, 0, 0)
        acciones.setSpacing(4)
        if self._filtros.clave_con_fecha() == fila[0]:
            acciones.addWidget(pildora_fecha(self._filtros))
        acciones.addWidget(accion(
            'simbologia.svg' if self._con_leyenda else 'simbologia-gris.svg',
            'Ocultar leyendas' if self._con_leyenda else 'Mostrar leyendas',
            self._alternar_leyenda))
        acciones.addWidget(accion('encuadrar.svg',
                                  'Encuadrar el mapa en esta capa o en sus municipios filtrados',
                                  lambda: self._control.encuadrar(fila[0])))
        if self._control.puede_descargar(fila[0]):
            acciones.addWidget(accion('descargar.svg',
                                      'Descargar como GeoPackage, con su municipio y periodo',
                                      lambda: self._control.descargar(fila[0])))
        acciones.addStretch(1)
        acciones.addWidget(bote('Quitar del mapa', lambda: self._control.quitar(fila)))
        return acciones

    def _caja(self, fila: Fila, asa: QWidget) -> QWidget:
        caja = QWidget()
        columna = QVBoxLayout(caja)
        if fila[0] != self.abierta:
            columna.setContentsMargins(0, 0, 4, 0)
            columna.addLayout(self._renglon(fila, asa))
            return caja
        set_role(caja, 'mapa-item-abierto')
        columna.setContentsMargins(6, 4, 8, 8)
        columna.setSpacing(4)
        titulo = QHBoxLayout()
        titulo.setContentsMargins(0, 0, 0, 0)
        titulo.setSpacing(4)
        titulo.addWidget(asa)
        titulo.addWidget(self._nombre(fila, True), 1)
        columna.addLayout(titulo)
        columna.addLayout(self._acciones(fila))
        leyenda = self._leyendas.de(fila[0]) if self._con_leyenda else None
        if leyenda is not None:
            columna.addWidget(leyenda)
        return caja

    def refrescar(self, filas: list[Fila]) -> None:
        self._filas = filas
        vaciar(self._layout)
        self._layout.addWidget(encabezado(len(filas), self._control.limpiar, self._switch,
                                          self._alternar_icono))
        cajas: list[QWidget] = []
        asas: list[QWidget] = []
        for fila in filas:
            asa = crear_asa()
            asa.setVisible(len(filas) > 1)
            caja = self._caja(fila, asa)
            self._layout.addWidget(caja)
            cajas.append(caja)
            asas.append(asa)
        self._arrastre.registrar(cajas, asas)
        self.setVisible(bool(filas) and not self._icono)
        self.boton.setVisible(bool(filas) and self._icono)
        self.boton.setToolTip(f'Capas seleccionadas ({len(filas)}): clic para abrir')
        QTimer.singleShot(0, self._ajustar)

    def _ajustar(self) -> None:
        self.setFixedWidth(ANCHO_TARJETA)
        alto = self.sizeHint().height()
        self.setFixedHeight(alto)
        self._control.acomodar()
