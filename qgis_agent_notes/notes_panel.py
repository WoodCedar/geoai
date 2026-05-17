from __future__ import annotations

from pathlib import Path

from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .core import ExportOptions, write_agent_notes
from .qgis_collect import collect_project_snapshot, project_output_base_dir, save_map_snapshot


class AgentNotesDockWidget(QDockWidget):
    """Dock widget for generating Markdown notes from a QGIS project."""

    def __init__(self, iface, parent=None):
        super().__init__("Agent Notes", parent)
        self.iface = iface
        self.last_output_dir: Path | None = None
        self._setup_ui()
        self.refresh_paths()

    def _setup_ui(self) -> None:
        container = QWidget()
        layout = QVBoxLayout(container)

        layout.addWidget(QLabel("QGIS project"))
        self.project_path_edit = QLineEdit()
        self.project_path_edit.setReadOnly(True)
        layout.addWidget(self.project_path_edit)

        layout.addWidget(QLabel("Notes folder"))
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setReadOnly(True)
        layout.addWidget(self.output_path_edit)

        layout.addWidget(QLabel("Layer scope"))
        self.scope_combo = QComboBox()
        self.scope_combo.addItem("All layers", "all")
        self.scope_combo.addItem("Visible layers only", "visible")
        self.scope_combo.addItem("Selected layers only", "selected")
        layout.addWidget(self.scope_combo)

        layout.addWidget(QLabel("Markdown language"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("中文", "zh")
        self.language_combo.addItem("English", "en")
        layout.addWidget(self.language_combo)

        self.clean_stale_check = QCheckBox("Clean stale layer cards before writing")
        self.clean_stale_check.setChecked(True)
        layout.addWidget(self.clean_stale_check)

        button_row = QHBoxLayout()
        self.generate_button = QPushButton("Generate Notes")
        self.generate_button.clicked.connect(self.generate_notes)
        button_row.addWidget(self.generate_button)

        self.open_button = QPushButton("Open Notes Folder")
        self.open_button.clicked.connect(self.open_notes_folder)
        button_row.addWidget(self.open_button)

        self.open_index_button = QPushButton("Open Index")
        self.open_index_button.clicked.connect(self.open_index)
        button_row.addWidget(self.open_index_button)
        layout.addLayout(button_row)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(120)
        layout.addWidget(self.status_text)

        self.setWidget(container)

    def refresh_paths(self) -> None:
        base_dir = project_output_base_dir()
        if base_dir is None:
            self.project_path_edit.setText("Save the QGIS project before generating notes.")
            self.output_path_edit.setText("")
            self.open_button.setEnabled(False)
            self.open_index_button.setEnabled(False)
            return

        from qgis.core import QgsProject

        self.project_path_edit.setText(QgsProject.instance().fileName())
        self.output_path_edit.setText(str(base_dir / "agent_notes"))
        self.open_button.setEnabled(True)
        self.open_index_button.setEnabled(True)

    def generate_notes(self) -> None:
        base_dir = project_output_base_dir()
        if base_dir is None:
            QMessageBox.warning(
                self,
                "Agent Notes",
                "Please save the QGIS project before generating notes.",
            )
            self.refresh_paths()
            return

        try:
            snapshot = collect_project_snapshot(self.iface)
            options = ExportOptions(
                language=self.language_combo.currentData(),
                layer_scope=self.scope_combo.currentData(),
                clean_stale=self.clean_stale_check.isChecked(),
            )
            output_dir = base_dir / options.output_dir_name
            snapshot_path = output_dir / "assets" / "map_snapshot.png"
            snapshot_saved = save_map_snapshot(self.iface, snapshot_path)

            relative_snapshot = Path("assets/map_snapshot.png") if snapshot_saved else None
            self.last_output_dir = write_agent_notes(
                snapshot,
                base_dir,
                map_snapshot_relative_path=relative_snapshot,
                options=options,
            )
            self.refresh_paths()
            self.status_text.setPlainText(
                "\n".join(
                    [
                        "Notes generated.",
                        f"Folder: {self.last_output_dir}",
                        f"Layers in project: {len(snapshot.layers)}",
                        f"Layer scope: {options.layer_scope}",
                        f"Map snapshot: {'saved' if snapshot_saved else 'not available'}",
                    ]
                )
            )
        except OSError as exc:
            QMessageBox.critical(self, "Agent Notes", f"Failed to write notes:\n{exc}")
            self.status_text.setPlainText(f"Failed to write notes:\n{exc}")

    def open_notes_folder(self) -> None:
        path_text = self.output_path_edit.text().strip()
        if not path_text:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path_text))

    def open_index(self) -> None:
        path_text = self.output_path_edit.text().strip()
        if not path_text:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path_text) / "index.md")))
