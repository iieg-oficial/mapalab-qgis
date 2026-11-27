from typing import Any, Callable, Iterable

from qgis.gui import QgsCheckableComboBox
from qgis.PyQt.QtCore import Qt

from ..layers.filtros import ZMG
from .lista_mapa import bote, contador_en
from .menu_combo import ROL_SECCION, como_menu

AYUDA_MUNICIPIO: str = ('Municipio: filtra la capa elegida y acerca el mapa a lo marcado. Sin '
                        'marcar ninguno se ve todo Jalisco. El menú trae atajos (Jalisco, la '
                        'Zona Metropolitana y las regiones) y, abajo, cada municipio. El filtro '
                        'se aplica al mapa, a la consulta por clic y a la descarga en GeoPackage.')

AYUDA_LIMPIAR: str = 'Quita la selección de municipios y vuelve a ver Jalisco completo.'

TEXTO_TODOS: str = 'Jalisco'

CLAVE_TODO: str = 'atajo:jalisco'

CLAVE_ZMG: str = 'atajo:zmg'

PREFIJO_REGION: str = 'atajo:region:'

VISIBLES: int = 14


class SelectorMunicipios:

    def __init__(self, al_cambiar: Callable[[], Any]) -> None:
        self._al_cambiar = al_cambiar
        self._silencio = False
        self._claves: set[str] = set()
        self._atajos: dict[str, tuple[str, ...]] = {}
        self.combo = QgsCheckableComboBox()
        self.combo.setDefaultText(TEXTO_TODOS)
        self.combo.setMaxVisibleItems(VISIBLES)
        self.combo.setToolTip(AYUDA_MUNICIPIO)
        como_menu(self.combo)
        self.combo.checkedItemsChanged.connect(lambda _: self._marcado())
        self.limpiar = bote(AYUDA_LIMPIAR, self._vaciar)
        self._contador = contador_en(self.limpiar, 0)
        self._actualizar()

    def hay(self) -> bool:
        return bool(self._claves)

    def marcados(self) -> list[str]:
        return [str(dato) for dato in self.combo.checkedItemsData() if dato in self._claves]

    def cargar(self, municipios: list[dict[str, Any]]) -> None:
        ordenados = sorted(municipios, key=lambda m: str(m.get('nombre')))
        nombres = {str(m.get('clave')): str(m.get('nombre') or '') for m in ordenados}
        regiones: dict[str, list[str]] = {}
        for municipio in ordenados:
            if municipio.get('region'):
                regiones.setdefault(str(municipio['region']), []).append(str(municipio['clave']))
        self._silencio = True
        self.combo.clear()
        self._claves = set(nombres)
        self._atajos = {}
        self._seccion('General')
        self._atajo(CLAVE_TODO, 'Jalisco completo (sin filtro)',
                    'Quita el filtro de municipio: se ve todo Jalisco.', ())
        zmg = [clave for clave in ZMG if clave in nombres]
        self._atajo(CLAVE_ZMG, 'ZMG: ' + ', '.join(nombres[clave] for clave in zmg),
                    'Zona Metropolitana de Guadalajara: ' + ', '.join(
                        nombres[clave] for clave in zmg), zmg)
        self._seccion('Regiones')
        for region in sorted(regiones):
            claves = regiones[region]
            self._atajo(PREFIJO_REGION + region, f'{region} · {len(claves)} municipios',
                        f'{region}: ' + ', '.join(nombres[clave] for clave in claves), claves)
        self._seccion('Municipios')
        for clave, nombre in nombres.items():
            self.combo.addItemWithCheckState(nombre, Qt.CheckState.Unchecked, clave)
        self._silencio = False
        self._actualizar()

    def fijar(self, claves: Iterable[str]) -> None:
        marcar = set(claves)
        self._silencio = True
        for indice in range(self.combo.count()):
            clave = self.combo.itemData(indice)
            if clave in self._claves:
                self.combo.setItemCheckState(
                    indice, Qt.CheckState.Checked if clave in marcar else Qt.CheckState.Unchecked)
        self._silencio = False
        self._actualizar()

    def _seccion(self, titulo: str) -> None:
        self.combo.addItemWithCheckState(titulo, Qt.CheckState.Unchecked, '')
        self.combo.setItemData(self.combo.count() - 1, True, ROL_SECCION)

    def _atajo(self, clave: str, texto: str, ayuda: str, claves: Iterable[str]) -> None:
        self.combo.addItemWithCheckState(texto, Qt.CheckState.Unchecked, clave)
        self.combo.setItemData(self.combo.count() - 1, ayuda, Qt.ItemDataRole.ToolTipRole)
        self._atajos[clave] = tuple(claves)

    def cuenta(self) -> int:
        restantes = set(self.marcados())
        if restantes and restantes == self._claves:
            return 1
        total = 0
        cubiertos = sorted((set(atajo) for atajo in self._atajos.values()
                            if atajo and set(atajo) <= restantes), key=len, reverse=True)
        for atajo in cubiertos:
            if restantes & atajo:
                total += 1
                restantes -= atajo
        return total + len(restantes)

    def _actualizar(self) -> None:
        total = self.cuenta()
        self.limpiar.setEnabled(total > 0)
        self._contador.setText(str(total))
        self._contador.setVisible(total > 0)

    def _vaciar(self) -> None:
        self.fijar(())
        self._al_cambiar()

    def _marcado(self) -> None:
        if self._silencio:
            return
        extra = [dato for dato in self.combo.checkedItemsData() if dato not in self._claves]
        if not extra:
            self._actualizar()
            self._al_cambiar()
            return
        self._silencio = True
        for indice in range(self.combo.count()):
            if self.combo.itemData(indice) in extra:
                self.combo.setItemCheckState(indice, Qt.CheckState.Unchecked)
        self._silencio = False
        atajo = next((self._atajos[dato] for dato in extra if dato in self._atajos), None)
        if atajo is not None:
            self._aplicar(set(atajo))

    def _aplicar(self, destino: set[str]) -> None:
        actuales = set(self.marcados())
        if not destino:
            nuevos: set[str] = set()
        elif destino <= actuales:
            nuevos = actuales - destino
        else:
            nuevos = actuales | destino
        self.fijar(nuevos)
        self._al_cambiar()
