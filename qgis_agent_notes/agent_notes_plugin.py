from __future__ import annotations

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMenu, QToolBar

from .notes_panel import AgentNotesDockWidget

TOOLBAR_OBJECT_NAME = "QGISAgentNotesToolbar"
MENU_TITLE = "&Agent Notes"


class AgentNotesPlugin:
    """QGIS plugin entry point for Agent Notes."""

    def __init__(self, iface):
        self.iface = iface
        self.actions = []
        self.menu = None
        self.toolbar = None
        self._dock = None

    def initGui(self):
        self.menu = QMenu(MENU_TITLE)
        self.iface.mainWindow().menuBar().addMenu(self.menu)

        self.toolbar = QToolBar("Agent Notes")
        self.toolbar.setObjectName(TOOLBAR_OBJECT_NAME)
        self.iface.addToolBar(self.toolbar)

        action = QAction(QIcon(":/images/themes/default/mActionFileSave.svg"), "Agent Notes", self.iface.mainWindow())
        action.setCheckable(True)
        action.triggered.connect(self.toggle_dock)
        self.menu.addAction(action)
        self.toolbar.addAction(action)
        self.actions.append(action)
        self.notes_action = action

    def toggle_dock(self, checked=False):
        if self._dock is None:
            self._dock = AgentNotesDockWidget(self.iface, self.iface.mainWindow())
            self._dock.visibilityChanged.connect(self._on_dock_visibility_changed)
            self.iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._dock)
        if self._dock.isVisible():
            self._dock.hide()
        else:
            self._dock.refresh_paths()
            self._dock.show()
            self._dock.raise_()
        self.notes_action.setChecked(self._dock.isVisible())

    def _on_dock_visibility_changed(self, visible):
        if hasattr(self, "notes_action"):
            self.notes_action.setChecked(visible)

    def unload(self):
        if self._dock is not None:
            self.iface.removeDockWidget(self._dock)
            self._dock.deleteLater()
            self._dock = None
        for action in self.actions:
            if self.toolbar is not None:
                self.toolbar.removeAction(action)
            if self.menu is not None:
                self.menu.removeAction(action)
        if self.toolbar is not None:
            self.iface.mainWindow().removeToolBar(self.toolbar)
            self.toolbar.deleteLater()
            self.toolbar = None
        if self.menu is not None:
            self.iface.mainWindow().menuBar().removeAction(self.menu.menuAction())
            self.menu.deleteLater()
            self.menu = None
        self.actions = []
