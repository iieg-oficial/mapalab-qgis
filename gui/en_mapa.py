from typing import Any, Callable, Optional

from qgis.core import QgsProject
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QWidget

from ..layers.grupos import quitar_grupo
from ..layers.orden import encuadrar_fila, mover_fila, municipios_de_fila
from ..layers.zoom import acercar_a_municipios
from ..layers.proyecto import limpiar_selecciones
from ..model.tree import find_node, has_wfs, is_downloadable
from .boton_icono import LADO_BOTON, BotonIcono
from .leyenda import Leyendas
from .lista_mapa import ANCHO_TARJETA, Fila, capas_en_mapa
from .sobre_mapa import MARGEN, Apilado, AvisoMapa, montar_tarjeta
from .tarjeta_capas import TarjetaEnMapa
from .tarjeta_filtros import TarjetaFiltros


class EnMapa:

    def __init__(self, iface: Any, arbol: Any, obtener_arbol: Callable[[], list],
                 quitar_nodo: Callable[[str], Any], filtros: Any, switch: QWidget,
                 al_descargar: Callable[[dict], Any], cajas: Callable[[], dict]) -> None:
        self._arbol = arbol
        self._cajas = cajas
        self._al_descargar = al_descargar
        self._filtros_mapa: Optional[TarjetaFiltros] = None
        self._aviso: Optional[AvisoMapa] = None
        self._obtener_arbol = obtener_arbol
        self._quitar_nodo = quitar_nodo
        self._filas: list[Fila] = []
        self._tarjeta: Optional[TarjetaEnMapa] = None
        self._botones: list[BotonIcono] = []
        canvas = iface.mapCanvas() if iface is not None else None
        self._canvas = canvas
        self._espera = QTimer(canvas)
        self._espera.setSingleShot(True)
        self._espera.timeout.connect(self._pintar)
        if canvas is not None:
            self._apilado = Apilado(canvas)
            self._filtros_mapa = TarjetaFiltros(filtros.widget, self.acomodar, canvas)
            leyendas = Leyendas(iface.layerTreeView, self.refrescar)
            self._tarjeta = TarjetaEnMapa(self, leyendas, filtros, switch, canvas)
            for tarjeta in (self._filtros_mapa, self._tarjeta):
                montar_tarjeta(tarjeta)
                self._apilado.agregar(tarjeta)
                self._apilado.agregar(tarjeta.boton)
            self._aviso = AvisoMapa(canvas)
            filtros.al_mostrar = self.refrescar
        self._raiz = QgsProject.instance().layerTreeRoot()
        self._raiz.addedChildren.connect(self._al_cambiar_arbol)
        self._raiz.removedChildren.connect(self._al_cambiar_arbol)

    def _al_cambiar_arbol(self, *args: Any) -> None:
        self.refrescar()

    def refrescar(self) -> None:
        self._espera.start(0)

    def abrir(self, clave: str) -> None:
        if self._tarjeta is not None:
            self._tarjeta.abierta = clave or None
            self.refrescar()

    def acomodar(self) -> None:
        if self._tarjeta is not None:
            self._apilado.acomodar()

    def encuadrar(self, clave: str) -> None:
        if self._canvas is None:
            return
        municipios = municipios_de_fila(clave)
        if municipios:
            acercar_a_municipios(self._canvas, self._cajas(), municipios, self.ocupado())
        else:
            encuadrar_fila(self._canvas, clave, self.ocupado())

    def crear_boton(self, icono: QIcon, ayuda: str,
                    al_clic: Callable[[], Any]) -> Optional[BotonIcono]:
        if self._canvas is None:
            return None
        boton = BotonIcono(icono, ayuda, al_clic, self._canvas)
        self._botones.append(boton)
        self._apilado.agregar(boton, primero=True)
        return boton

    def ocupado(self) -> int:
        if self._tarjeta is None or self._filtros_mapa is None:
            return 0
        if not (self._tarjeta.isHidden() and self._filtros_mapa.isHidden()):
            return ANCHO_TARJETA + 2 * MARGEN
        botones = [self._tarjeta.boton, self._filtros_mapa.boton, *self._botones]
        return LADO_BOTON + 2 * MARGEN if any(not b.isHidden() for b in botones) else 0

    def avisar(self, texto: str) -> None:
        if self._aviso is not None:
            self._aviso.mostrar(texto)

    def _nodo(self, clave: str) -> Optional[dict]:
        return find_node(self._obtener_arbol(), clave)

    def puede_descargar(self, clave: str) -> bool:
        nodo = self._nodo(clave)
        return bool(nodo and nodo.get('wmsConfig') and has_wfs(nodo) and is_downloadable(nodo))

    def descargar(self, clave: str) -> None:
        nodo = self._nodo(clave)
        if nodo is not None:
            self._al_descargar(nodo)

    def limpiar(self) -> None:
        for fila in list(self._filas):
            self.quitar(fila)
        limpiar_selecciones()

    def mover(self, origen: int, destino: int) -> None:
        if mover_fila([fila[0] for fila in self._filas], origen, destino):
            self.refrescar()

    def _pintar(self) -> None:
        self._filas = capas_en_mapa(self._obtener_arbol())
        if self._tarjeta is not None and self._filtros_mapa is not None:
            self._tarjeta.refrescar(self._filas)
            self._filtros_mapa.refrescar()

    def elegir(self, clave: str) -> None:
        self._arbol.seleccionar(clave)

    def quitar(self, fila: Fila) -> None:
        if fila[2]:
            quitar_grupo(fila[0])
        else:
            self._quitar_nodo(fila[0])

    def cerrar(self) -> None:
        for senal in (self._raiz.addedChildren, self._raiz.removedChildren):
            try:
                senal.disconnect(self._al_cambiar_arbol)
            except TypeError:
                pass
        for widget in (self._tarjeta, self._filtros_mapa, self._aviso, *self._botones):
            if widget is not None:
                widget.deleteLater()
        self._tarjeta = self._filtros_mapa = self._aviso = None
        self._botones = []
