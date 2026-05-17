from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

PLUGIN_VERSION = "0.3.0"
STATE_FILE = ".agent_notes_state.json"
LAYER_FILENAME_LIMIT = 80


@dataclass(frozen=True)
class ExportOptions:
    language: str = "zh"
    layer_scope: str = "all"
    clean_stale: bool = True
    output_dir_name: str = "agent_notes"


@dataclass(frozen=True)
class FieldSnapshot:
    name: str
    type_name: str
    null_count: int | None = None
    sample_values: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LayerSnapshot:
    name: str
    layer_type: str
    source: Path | str
    crs: str
    extent: str
    feature_count: int | None
    raster_size: str | None
    fields: list[FieldSnapshot]
    is_valid: bool
    is_editable: bool
    visible: bool = True
    selected: bool = False
    group_path: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ProjectSnapshot:
    name: str
    project_path: Path | str
    crs: str
    extent: str
    generated_at: str
    layers: list[LayerSnapshot]
    qgis_version: str = ""
    plugin_version: str = PLUGIN_VERSION


def write_agent_notes(
    project: ProjectSnapshot,
    base_dir: Path | str,
    map_snapshot_relative_path: Path | str | None = None,
    options: ExportOptions | None = None,
) -> Path:
    """Write Markdown notes for a QGIS project snapshot."""
    options = options or ExportOptions()
    base_path = Path(base_dir)
    output_dir = base_path / options.output_dir_name
    layers_dir = output_dir / "layers"
    assets_dir = output_dir / "assets"
    layers_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)

    previous_state = _load_state(output_dir)
    layers = _filtered_layers(project.layers, options.layer_scope)
    layer_paths = _write_layer_cards(layers, layers_dir, options.language)
    if options.clean_stale:
        _clean_stale_layer_cards(layers_dir, [relative for _, relative in layer_paths])

    snapshot_path = (
        _normalize_markdown_path(map_snapshot_relative_path)
        if map_snapshot_relative_path
        else None
    )
    current_state = _state_for(project, layers, layer_paths)
    changes = _compare_states(previous_state, current_state)

    _write_text(output_dir / "summary.md", _render_summary(project, layers, options.language))
    _write_text(output_dir / "project.md", _render_project(project, layers, snapshot_path, options.language))
    _write_text(output_dir / "data_inventory.md", _render_data_inventory(layers, layer_paths, options.language))
    _write_text(output_dir / "quality_report.md", _render_quality_report(layers, options.language))
    _write_text(output_dir / "map_view.md", _render_map_view(project, layers, snapshot_path, options.language))
    _write_text(output_dir / "agent_prompt.md", _render_agent_prompt(project, layer_paths, options.language))
    _write_text(output_dir / "agent_context.md", _render_agent_context(project, layer_paths, options.language))
    _write_text(output_dir / "changes.md", _render_changes(changes, options.language))
    _write_text(output_dir / "index.md", _render_index(project, layers, layer_paths, snapshot_path, options.language))
    _append_history(output_dir / "history.md", project, layers, changes, options.language)
    _write_state(output_dir, current_state)

    return output_dir


def _filtered_layers(layers: Iterable[LayerSnapshot], scope: str) -> list[LayerSnapshot]:
    if scope == "visible":
        return [layer for layer in layers if layer.visible]
    if scope == "selected":
        return [layer for layer in layers if layer.selected]
    return list(layers)


def _write_layer_cards(
    layers: Iterable[LayerSnapshot], layers_dir: Path, language: str
) -> list[tuple[LayerSnapshot, str]]:
    used_names: dict[str, int] = {}
    layer_paths: list[tuple[LayerSnapshot, str]] = []

    for layer in layers:
        filename = _unique_filename(_safe_filename(layer.name), used_names)
        relative_path = f"layers/{filename}"
        _write_text(layers_dir / filename, _render_layer(layer, language))
        layer_paths.append((layer, relative_path))

    return layer_paths


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[\\/:*?\"<>|\[\]\(\)\s]+", "_", name.strip())
    safe = re.sub(r"_+", "_", safe).strip("._")
    if not safe:
        safe = "layer"
    if len(safe) > LAYER_FILENAME_LIMIT:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
        safe = f"{safe[:LAYER_FILENAME_LIMIT]}_{digest}"
    return f"{safe}.md"


def _unique_filename(filename: str, used_names: dict[str, int]) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    count = used_names.get(filename, 0) + 1
    used_names[filename] = count
    if count == 1:
        return filename
    return f"{stem}_{count}{suffix}"


def _clean_stale_layer_cards(layers_dir: Path, current_relative_paths: list[str]) -> None:
    current_names = {Path(path).name for path in current_relative_paths}
    for path in layers_dir.glob("*.md"):
        if path.name not in current_names:
            path.unlink()


def _render_index(
    project: ProjectSnapshot,
    layers: list[LayerSnapshot],
    layer_paths: list[tuple[LayerSnapshot, str]],
    snapshot_path: str | None,
    language: str,
) -> str:
    heading = _text(language, "index_title", project=project.name)
    lines = [
        f"# {heading}",
        "",
        f"- {_text(language, 'summary')}: [Summary](summary.md)",
        f"- {_text(language, 'project_notes')}: [Project](project.md)",
        f"- {_text(language, 'data_inventory')}: [Data inventory](data_inventory.md)",
        f"- {_text(language, 'quality_report')}: [Quality report](quality_report.md)",
        f"- {_text(language, 'changes')}: [Changes](changes.md)",
        f"- {_text(language, 'history')}: [History](history.md)",
        f"- {_text(language, 'agent_context')}: [Agent context](agent_context.md)",
        f"- {_text(language, 'agent_prompt')}: [Agent prompt](agent_prompt.md)",
        f"- {_text(language, 'generated_at')}: {project.generated_at}",
        f"- {_text(language, 'layer_count')}: {len(layers)}",
        "",
    ]
    if snapshot_path:
        lines.extend([f"![{_text(language, 'current_map')}]({snapshot_path})", ""])

    lines.extend([f"## {_text(language, 'layer_cards')}", ""])
    if layer_paths:
        for layer, relative_path in layer_paths:
            lines.append(f"- [{_escape_link_text(layer.name)}]({relative_path})")
    else:
        lines.append(_text(language, "no_layers"))
    lines.append("")
    return "\n".join(lines)


def _render_summary(project: ProjectSnapshot, layers: list[LayerSnapshot], language: str) -> str:
    invalid_count = sum(1 for layer in layers if not layer.is_valid)
    raster_count = sum(1 for layer in layers if layer.layer_type == "raster")
    vector_count = sum(1 for layer in layers if layer.layer_type == "vector")
    lines = [
        f"# {_text(language, 'summary_title')}",
        "",
        f"- {_text(language, 'project_name')}: {project.name}",
        f"- {_text(language, 'project_file')}: {_path_text(project.project_path)}",
        f"- {_text(language, 'crs')}: {project.crs}",
        f"- {_text(language, 'extent')}: {project.extent}",
        f"- {_text(language, 'generated_at')}: {project.generated_at}",
        f"- {_text(language, 'qgis_version')}: {project.qgis_version or 'unknown'}",
        f"- {_text(language, 'plugin_version')}: {project.plugin_version or PLUGIN_VERSION}",
        f"- {_text(language, 'layer_count')}: {len(layers)}",
        f"- {_text(language, 'vector_layers')}: {vector_count}",
        f"- {_text(language, 'raster_layers')}: {raster_count}",
        f"- {_text(language, 'invalid_layers')}: {invalid_count}",
        "",
    ]
    return "\n".join(lines)


def _render_project(
    project: ProjectSnapshot,
    layers: list[LayerSnapshot],
    snapshot_path: str | None,
    language: str,
) -> str:
    lines = [
        f"# {_text(language, 'project_notes_title', project=project.name)}",
        "",
        f"- {_text(language, 'project_file')}: {_path_text(project.project_path)}",
        f"- {_text(language, 'crs')}: {project.crs}",
        f"- {_text(language, 'extent')}: {project.extent}",
        f"- {_text(language, 'layer_count')}: {len(layers)}",
        f"- {_text(language, 'generated_at')}: {project.generated_at}",
        f"- {_text(language, 'qgis_version')}: {project.qgis_version or 'unknown'}",
        f"- {_text(language, 'plugin_version')}: {project.plugin_version or PLUGIN_VERSION}",
    ]
    if snapshot_path:
        lines.append(f"- {_text(language, 'map_snapshot')}: {snapshot_path}")
    lines.extend(["", f"## {_text(language, 'layer_list')}", ""])
    if layers:
        for layer in layers:
            lines.append(f"- {layer.name} ({layer.layer_type})")
    else:
        lines.append(_text(language, "no_layers"))
    lines.append("")
    return "\n".join(lines)


def _render_layer(layer: LayerSnapshot, language: str) -> str:
    source_path, source_detail = _split_source(layer.source)
    source_link = _source_link(source_path)
    group = _group_text(layer.group_path)
    lines = [
        f"# {layer.name}",
        "",
        f"- {_text(language, 'type')}: {layer.layer_type}",
        f"- {_text(language, 'source')}: {source_link}",
        f"- {_text(language, 'source_detail')}: `{_path_text(layer.source)}`",
        f"- {_text(language, 'source_layer')}: {source_detail or 'none'}",
        f"- {_text(language, 'group')}: {group}",
        f"- {_text(language, 'crs')}: {layer.crs}",
        f"- {_text(language, 'extent')}: {layer.extent}",
        f"- {_text(language, 'valid')}: {_yes_no(layer.is_valid, language)}",
        f"- {_text(language, 'editable')}: {_yes_no(layer.is_editable, language)}",
        f"- {_text(language, 'visible')}: {_yes_no(layer.visible, language)}",
        f"- {_text(language, 'selected')}: {_yes_no(layer.selected, language)}",
    ]
    if layer.feature_count is not None:
        lines.append(f"- {_text(language, 'feature_count')}: {layer.feature_count}")
    if layer.raster_size:
        lines.append(f"- {_text(language, 'raster_size')}: {layer.raster_size}")

    lines.extend(["", f"## {_text(language, 'fields')}", ""])
    if layer.fields:
        lines.extend(
            [
                f"| {_text(language, 'field')} | {_text(language, 'field_type')} | {_text(language, 'nulls')} | {_text(language, 'samples')} |",
                "| --- | --- | --- | --- |",
            ]
        )
        for field_snapshot in layer.fields:
            sample_text = "; ".join(field_snapshot.sample_values[:5]) if field_snapshot.sample_values else ""
            null_count = "" if field_snapshot.null_count is None else str(field_snapshot.null_count)
            lines.append(
                "| "
                f"{_escape_table_cell(field_snapshot.name)} | "
                f"{_escape_table_cell(field_snapshot.type_name)} | "
                f"{_escape_table_cell(null_count)} | "
                f"{_escape_table_cell(sample_text)} |"
            )
    else:
        lines.append(_text(language, "no_fields"))

    lines.extend(
        [
            "",
            f"## {_text(language, 'notes')}",
            "",
            _text(language, "layer_note"),
            "",
        ]
    )
    return "\n".join(lines)


def _render_data_inventory(
    layers: list[LayerSnapshot],
    layer_paths: list[tuple[LayerSnapshot, str]],
    language: str,
) -> str:
    path_by_name = {id(layer): path for layer, path in layer_paths}
    lines = [
        f"# {_text(language, 'data_inventory')}",
        "",
        "| Layer | Type | Group | CRS | Count / size | Status | Source | Card |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for layer in layers:
        count = str(layer.feature_count) if layer.feature_count is not None else (layer.raster_size or "")
        status = "valid" if layer.is_valid else "invalid"
        source_path, _ = _split_source(layer.source)
        lines.append(
            "| "
            f"{_escape_table_cell(layer.name)} | "
            f"{_escape_table_cell(layer.layer_type)} | "
            f"{_escape_table_cell(_group_text(layer.group_path))} | "
            f"{_escape_table_cell(layer.crs)} | "
            f"{_escape_table_cell(count)} | "
            f"{_escape_table_cell(status)} | "
            f"{_escape_table_cell(_path_text(source_path))} | "
            f"[card]({path_by_name[id(layer)]}) |"
        )
    if not layers:
        lines.append("| none |  |  |  |  |  |  |  |")
    lines.append("")
    return "\n".join(lines)


def _render_quality_report(layers: list[LayerSnapshot], language: str) -> str:
    invalid_layers = [layer for layer in layers if not layer.is_valid]
    missing_sources = [layer for layer in layers if not str(layer.source).strip()]
    crs_values = sorted({layer.crs for layer in layers if layer.crs and layer.crs != "unknown"})
    lines = [
        f"# {_text(language, 'quality_report')}",
        "",
        f"## {_text(language, 'invalid_layers')}",
        "",
    ]
    lines.extend(_bullet_names(invalid_layers, language))
    lines.extend(["", f"## {_text(language, 'missing_sources')}", ""])
    lines.extend(_bullet_names(missing_sources, language))
    lines.extend(["", f"## {_text(language, 'crs_review')}", ""])
    if len(crs_values) > 1:
        lines.append(_text(language, "multiple_crs", crs=", ".join(crs_values)))
    elif crs_values:
        lines.append(_text(language, "single_crs", crs=crs_values[0]))
    else:
        lines.append(_text(language, "no_crs"))
    lines.append("")
    return "\n".join(lines)


def _render_map_view(
    project: ProjectSnapshot,
    layers: list[LayerSnapshot],
    snapshot_path: str | None,
    language: str,
) -> str:
    visible_layers = [layer.name for layer in layers if layer.visible]
    lines = [
        f"# {_text(language, 'map_view')}",
        "",
        f"- {_text(language, 'extent')}: {project.extent}",
        f"- {_text(language, 'crs')}: {project.crs}",
        f"- {_text(language, 'snapshot')}: {snapshot_path or _text(language, 'not_available')}",
        "",
        f"## {_text(language, 'visible_layers')}",
        "",
    ]
    if visible_layers:
        lines.extend(f"- {name}" for name in visible_layers)
    else:
        lines.append(_text(language, "no_layers"))
    lines.append("")
    return "\n".join(lines)


def _render_agent_prompt(
    project: ProjectSnapshot,
    layer_paths: list[tuple[LayerSnapshot, str]],
    language: str,
) -> str:
    lines = [
        f"# {_text(language, 'agent_prompt')}",
        "",
        _text(language, "agent_prompt_body", project=project.name),
        "",
        "- Read `summary.md` first.",
        "- Read `data_inventory.md` before choosing a layer.",
        "- Read the relevant layer card before using a source dataset.",
        "- Treat source datasets and the QGIS project as authoritative.",
        "",
        "## Layer cards",
        "",
    ]
    for layer, relative_path in layer_paths:
        lines.append(f"- {layer.name}: `{relative_path}`")
    lines.append("")
    return "\n".join(lines)


def _render_agent_context(
    project: ProjectSnapshot,
    layer_paths: list[tuple[LayerSnapshot, str]],
    language: str,
) -> str:
    lines = [
        f"# Agent Context: {project.name}",
        "",
        _text(language, "agent_context_body"),
        "",
        f"- {_text(language, 'project_file')}: {_path_text(project.project_path)}",
        f"- {_text(language, 'crs')}: {project.crs}",
        f"- {_text(language, 'extent')}: {project.extent}",
        "",
        "## Read first",
        "",
        "- summary.md",
        "- data_inventory.md",
        "- quality_report.md",
        "",
        "## Layers",
        "",
    ]
    for layer, relative_path in layer_paths:
        lines.append(f"- {layer.name} -> {relative_path}")

    lines.extend(["", "## Rule", "", _text(language, "authoritative_note"), ""])
    return "\n".join(lines)


def _render_changes(changes: dict[str, list[str]], language: str) -> str:
    lines = [f"# {_text(language, 'changes')}", ""]
    for key, heading in (
        ("added", _text(language, "added_layers")),
        ("removed", _text(language, "removed_layers")),
        ("changed", _text(language, "changed_layers")),
    ):
        lines.extend([f"## {heading}", ""])
        if changes[key]:
            lines.extend(f"- {item}" for item in changes[key])
        else:
            lines.append(_text(language, "none"))
        lines.append("")
    if not any(changes.values()):
        lines.append(_text(language, "no_changes"))
        lines.append("")
    return "\n".join(lines)


def _append_history(
    history_path: Path,
    project: ProjectSnapshot,
    layers: list[LayerSnapshot],
    changes: dict[str, list[str]],
    language: str,
) -> None:
    if history_path.exists():
        text = history_path.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
    else:
        text = f"# {_text(language, 'history')}\n\n"
    entry = [
        f"## {project.generated_at}",
        "",
        f"- {_text(language, 'plugin_version')}: {project.plugin_version or PLUGIN_VERSION}",
        f"- {_text(language, 'layer_count')}: {len(layers)}",
        f"- {_text(language, 'added_layers')}: {len(changes['added'])}",
        f"- {_text(language, 'removed_layers')}: {len(changes['removed'])}",
        f"- {_text(language, 'changed_layers')}: {len(changes['changed'])}",
        "",
    ]
    _write_text(history_path, text + "\n".join(entry))


def _load_state(output_dir: Path) -> dict:
    path = output_dir / STATE_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_state(output_dir: Path, state: dict) -> None:
    _write_text(output_dir / STATE_FILE, json.dumps(state, ensure_ascii=False, indent=2))


def _state_for(
    project: ProjectSnapshot,
    layers: list[LayerSnapshot],
    layer_paths: list[tuple[LayerSnapshot, str]],
) -> dict:
    return {
        "project": project.name,
        "generated_at": project.generated_at,
        "layers": [
            {
                "name": layer.name,
                "source": _path_text(layer.source),
                "crs": layer.crs,
                "fields": [field_snapshot.name for field_snapshot in layer.fields],
                "card": relative_path,
            }
            for layer, relative_path in layer_paths
        ],
    }


def _compare_states(previous: dict, current: dict) -> dict[str, list[str]]:
    previous_layers = {layer["name"]: layer for layer in previous.get("layers", [])}
    current_layers = {layer["name"]: layer for layer in current.get("layers", [])}
    added = sorted(set(current_layers) - set(previous_layers))
    removed = sorted(set(previous_layers) - set(current_layers))
    changed = sorted(
        name
        for name in set(previous_layers) & set(current_layers)
        if previous_layers[name] != current_layers[name]
    )
    return {"added": added, "removed": removed, "changed": changed}


def _bullet_names(layers: list[LayerSnapshot], language: str) -> list[str]:
    if not layers:
        return [_text(language, "none")]
    return [f"- {layer.name}" for layer in layers]


def _split_source(source: Path | str) -> tuple[str, str]:
    source_text = _path_text(source)
    if "|" not in source_text:
        return source_text, ""
    source_path, detail = source_text.split("|", 1)
    return source_path, detail


def _source_link(source_path: str) -> str:
    if not source_path:
        return "missing"
    if source_path.startswith(("http://", "https://")):
        return f"[source]({source_path})"
    return f"[source]({_path_text(source_path)})"


def _group_text(group_path: tuple[str, ...]) -> str:
    return " / ".join(group_path) if group_path else "none"


def _yes_no(value: bool, language: str) -> str:
    if language == "en":
        return "yes" if value else "no"
    return "是" if value else "否"


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _path_text(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def _normalize_markdown_path(path: Path | str) -> str:
    return _path_text(path)


def _escape_table_cell(value: object) -> str:
    text = str(value)
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("[", "\\[")
    text = text.replace("]", "\\]")
    return text.replace("\n", "<br>")


def _escape_link_text(value: str) -> str:
    return value.replace("[", "\\[").replace("]", "\\]")


def _text(language: str, key: str, **kwargs) -> str:
    strings = EN_STRINGS if language == "en" else ZH_STRINGS
    template = strings.get(key, EN_STRINGS.get(key, key))
    return template.format(**kwargs)


EN_STRINGS = {
    "index_title": "{project}",
    "summary": "Summary",
    "project_notes": "Project notes",
    "data_inventory": "Data inventory",
    "quality_report": "Quality report",
    "changes": "Changes",
    "history": "History",
    "agent_context": "Agent context",
    "agent_prompt": "Agent prompt",
    "generated_at": "Generated at",
    "layer_count": "Layer count",
    "current_map": "Current map",
    "layer_cards": "Layer cards",
    "no_layers": "No layers.",
    "summary_title": "Summary",
    "project_name": "Project name",
    "project_file": "Project file",
    "crs": "CRS",
    "extent": "Extent",
    "qgis_version": "QGIS version",
    "plugin_version": "Plugin version",
    "vector_layers": "Vector layers",
    "raster_layers": "Raster layers",
    "invalid_layers": "Invalid layers",
    "project_notes_title": "Project notes: {project}",
    "map_snapshot": "Map snapshot",
    "layer_list": "Layer list",
    "type": "Type",
    "source": "Source",
    "source_detail": "Source detail",
    "source_layer": "Source layer",
    "group": "Group",
    "valid": "Valid",
    "editable": "Editable",
    "visible": "Visible",
    "selected": "Selected",
    "feature_count": "Feature count",
    "raster_size": "Raster size",
    "fields": "Fields",
    "field": "Field",
    "field_type": "Type",
    "nulls": "Nulls",
    "samples": "Samples",
    "no_fields": "No field information.",
    "notes": "Notes",
    "layer_note": "This file is a layer card. The source dataset remains authoritative.",
    "missing_sources": "Missing data sources",
    "crs_review": "CRS review",
    "multiple_crs": "Multiple CRS values found: {crs}",
    "single_crs": "All layers with CRS metadata use {crs}.",
    "no_crs": "No CRS metadata available.",
    "map_view": "Map view",
    "snapshot": "Snapshot",
    "not_available": "not available",
    "visible_layers": "Visible layers",
    "agent_prompt_body": "Use these Markdown files to understand the QGIS project `{project}` before choosing data or running analysis.",
    "agent_context_body": "This is the compact Markdown entry point for agents.",
    "authoritative_note": "Source datasets and the QGIS project are authoritative; Markdown files are documentation and indexes.",
    "added_layers": "Added layers",
    "removed_layers": "Removed layers",
    "changed_layers": "Changed layers",
    "none": "None.",
    "no_changes": "No previous export changes were detected.",
}


ZH_STRINGS = {
    "index_title": "{project}",
    "summary": "项目摘要",
    "project_notes": "工程说明",
    "data_inventory": "数据清单",
    "quality_report": "质量报告",
    "changes": "变化记录",
    "history": "生成历史",
    "agent_context": "Agent 索引",
    "agent_prompt": "Agent 提示词",
    "generated_at": "生成时间",
    "layer_count": "图层数量",
    "current_map": "当前地图",
    "layer_cards": "图层卡片",
    "no_layers": "没有图层。",
    "summary_title": "项目摘要",
    "project_name": "项目名称",
    "project_file": "工程文件",
    "crs": "坐标系",
    "extent": "范围",
    "qgis_version": "QGIS 版本",
    "plugin_version": "插件版本",
    "vector_layers": "矢量图层",
    "raster_layers": "栅格图层",
    "invalid_layers": "无效图层",
    "project_notes_title": "工程说明：{project}",
    "map_snapshot": "地图截图",
    "layer_list": "图层清单",
    "type": "类型",
    "source": "数据源",
    "source_detail": "完整数据源",
    "source_layer": "数据源子层",
    "group": "分组",
    "valid": "有效",
    "editable": "可编辑",
    "visible": "可见",
    "selected": "已选中",
    "feature_count": "要素数量",
    "raster_size": "栅格尺寸",
    "fields": "字段",
    "field": "字段",
    "field_type": "类型",
    "nulls": "空值数",
    "samples": "示例值",
    "no_fields": "无字段信息。",
    "notes": "说明",
    "layer_note": "这个文件是图层说明卡片。原始数据仍以数据源文件为准。",
    "missing_sources": "缺失数据源",
    "crs_review": "坐标系检查",
    "multiple_crs": "发现多个坐标系：{crs}",
    "single_crs": "所有带坐标系信息的图层都使用 {crs}。",
    "no_crs": "没有可用坐标系信息。",
    "map_view": "地图视图",
    "snapshot": "截图",
    "not_available": "不可用",
    "visible_layers": "可见图层",
    "agent_prompt_body": "在选择数据或执行分析前，先读取这些 Markdown 文件来理解 QGIS 工程 `{project}`。",
    "agent_context_body": "这是给 agent 快速读取的 Markdown 入口。",
    "authoritative_note": "原始数据和 QGIS 工程才是准确信息来源；Markdown 文件只是说明和索引。",
    "added_layers": "新增图层",
    "removed_layers": "移除图层",
    "changed_layers": "变化图层",
    "none": "无。",
    "no_changes": "没有检测到相对上次导出的变化。",
}
