import os
from typing import Any, Optional

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .gui.dock import MapaLabDock
from .identidad import icono_guardado

MENU_TITLE: str = 'MapaLab'

TEXTO_SERVIDOR: str = 'Cambiar servidor…'

TEXTO_COMPARTIDO: str = 'Abrir mapa compartido…'


class MapaLabPlugin:

    def __init__(self, iface: Any) -> None:
        self._iface = iface
        self._action: Optional[QAction] = None
        self._servidor: Optional[QAction] = None
        self._compartido: Optional[QAction] = None
        self._dock: Optional[MapaLabDock] = None

    def _icon(self) -> QIcon:
        oficial = icono_guardado()
        if oficial:
            return QIcon(oficial)
        path = os.path.join(os.path.dirname(__file__), 'icon.svg')
        return QIcon(path) if os.path.exists(path) else QIcon()

    def initGui(self) -> None:
        self._action = QAction(self._icon(), MENU_TITLE, self._iface.mainWindow())
        self._action.setCheckable(True)
        self._action.triggered.connect(self._toggle)

        self._servidor = QAction(TEXTO_SERVIDOR, self._iface.mainWindow())
        self._servidor.triggered.connect(self._cambiar_servidor)
        self._compartido = QAction(TEXTO_COMPARTIDO, self._iface.mainWindow())
        self._compartido.triggered.connect(self._abrir_compartido)

        self._iface.addToolBarIcon(self._action)
        self._iface.addPluginToWebMenu(MENU_TITLE, self._action)
        self._iface.addPluginToWebMenu(MENU_TITLE, self._compartido)
        self._iface.addPluginToWebMenu(MENU_TITLE, self._servidor)

    def _asegurar_dock(self) -> MapaLabDock:
        if self._dock is None:
            self._dock = MapaLabDock(self._iface, self._iface.mainWindow())
            self._dock.visibilityChanged.connect(self._on_visibility)
            self._iface.addDockWidget(Qt.RightDockWidgetArea, self._dock)
            if self._action is not None:
                self._action.setIcon(self._icon())
        return self._dock

    def _toggle(self, checked: bool) -> None:
        self._asegurar_dock().setVisible(checked)

    def _cambiar_servidor(self) -> None:
        dock = self._asegurar_dock()
        dock.setVisible(True)
        dock.raise_()
        dock.mostrar_servidor()

    def _abrir_compartido(self) -> None:
        dock = self._asegurar_dock()
        dock.setVisible(True)
        dock.abrir_compartido()

    def _on_visibility(self, visible: bool) -> None:
        if self._action is not None:
            self._action.setChecked(visible)

    def unload(self) -> None:
        if self._dock is not None:
            self._dock.cerrar()
            self._iface.removeDockWidget(self._dock)
            self._dock.deleteLater()
            self._dock = None

        if self._action is not None:
            self._iface.removeToolBarIcon(self._action)
            self._iface.removePluginWebMenu(MENU_TITLE, self._action)
            self._action = None

        for accion in (self._servidor, self._compartido):
            if accion is not None:
                self._iface.removePluginWebMenu(MENU_TITLE, accion)
        self._servidor = None
        self._compartido = None
