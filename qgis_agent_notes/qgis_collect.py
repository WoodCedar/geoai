from __future__ import annotations

from datetime import datetime
from pathlib import Path

from .core import FieldSnapshot, LayerSnapshot, ProjectSnapshot


def collect_project_snapshot(iface) -> ProjectSnapshot:
    """Collect project and layer metadata from the current QGIS session."""
    from qgis.core import QgsMapLayer, QgsProject

    project = QgsProject.instance()
    project_path = Path(project.fileName()) if project.fileName() else Path()
    project_name = project.title() or project.baseName() or "Unsaved QGIS Project"
    crs = _authid(project.crs())
    extent = _extent_text(iface.mapCanvas().extent())
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    layers: list[LayerSnapshot] = []
    for layer in project.mapLayers().values():
        layer_type = _layer_type_name(layer, QgsMapLayer)
        fields = _field_snapshots(layer) if layer_type == "vector" else []
        layers.append(
            LayerSnapshot(
                name=layer.name(),
                layer_type=layer_type,
                source=layer.source(),
                crs=_authid(layer.crs()),
                extent=_extent_text(layer.extent()) if layer.isValid() else "unknown",
                feature_count=_feature_count(layer, layer_type),
                raster_size=_raster_size(layer, layer_type),
                fields=fields,
                is_valid=bool(layer.isValid()),
                is_editable=bool(getattr(layer, "isEditable", lambda: False)()),
            )
        )

    return ProjectSnapshot(
        name=project_name,
        project_path=project_path,
        crs=crs,
        extent=extent,
        generated_at=generated_at,
        layers=layers,
    )


def project_output_base_dir() -> Path | None:
    """Return the directory beside the current saved project, if available."""
    from qgis.core import QgsProject

    project_file = QgsProject.instance().fileName()
    if not project_file:
        return None
    return Path(project_file).resolve().parent


def save_map_snapshot(iface, output_path: Path) -> bool:
    """Save the current QGIS map canvas as an image."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas = iface.mapCanvas()
    if hasattr(canvas, "saveAsImage"):
        canvas.saveAsImage(str(output_path))
        return output_path.exists()
    if hasattr(canvas, "grab"):
        pixmap = canvas.grab()
        return bool(pixmap.save(str(output_path)))
    return False


def _layer_type_name(layer, QgsMapLayer) -> str:
    layer_type = layer.type()
    if layer_type == QgsMapLayer.VectorLayer:
        return "vector"
    if layer_type == QgsMapLayer.RasterLayer:
        return "raster"
    return "other"


def _field_snapshots(layer) -> list[FieldSnapshot]:
    fields = []
    for field in layer.fields():
        type_name = field.typeName() or str(field.type())
        fields.append(FieldSnapshot(field.name(), type_name))
    return fields


def _feature_count(layer, layer_type: str) -> int | None:
    if layer_type != "vector":
        return None
    try:
        return int(layer.featureCount())
    except Exception:
        return None


def _raster_size(layer, layer_type: str) -> str | None:
    if layer_type != "raster":
        return None
    try:
        return f"{layer.width()} x {layer.height()}"
    except Exception:
        return None


def _authid(crs) -> str:
    try:
        authid = crs.authid()
    except Exception:
        authid = ""
    return authid or "unknown"


def _extent_text(extent) -> str:
    try:
        return (
            f"{extent.xMinimum():.6f},"
            f"{extent.yMinimum():.6f},"
            f"{extent.xMaximum():.6f},"
            f"{extent.yMaximum():.6f}"
        )
    except Exception:
        return "unknown"
