from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class FieldSnapshot:
    name: str
    type_name: str


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


@dataclass(frozen=True)
class ProjectSnapshot:
    name: str
    project_path: Path | str
    crs: str
    extent: str
    generated_at: str
    layers: list[LayerSnapshot]


def write_agent_notes(
    project: ProjectSnapshot,
    base_dir: Path | str,
    map_snapshot_relative_path: Path | str | None = None,
) -> Path:
    """Write Markdown notes for a QGIS project snapshot."""
    base_path = Path(base_dir)
    output_dir = base_path / "agent_notes"
    layers_dir = output_dir / "layers"
    layers_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "assets").mkdir(parents=True, exist_ok=True)

    layer_paths = _write_layer_cards(project.layers, layers_dir)
    snapshot_path = (
        _normalize_markdown_path(map_snapshot_relative_path)
        if map_snapshot_relative_path
        else None
    )

    _write_text(output_dir / "project.md", _render_project(project, snapshot_path))
    _write_text(output_dir / "agent_context.md", _render_agent_context(project, layer_paths))
    _write_text(output_dir / "index.md", _render_index(project, layer_paths, snapshot_path))

    return output_dir


def _write_layer_cards(
    layers: Iterable[LayerSnapshot], layers_dir: Path
) -> list[tuple[LayerSnapshot, str]]:
    used_names: dict[str, int] = {}
    layer_paths: list[tuple[LayerSnapshot, str]] = []

    for layer in layers:
        filename = _unique_filename(_safe_filename(layer.name), used_names)
        relative_path = f"layers/{filename}"
        _write_text(layers_dir / filename, _render_layer(layer))
        layer_paths.append((layer, relative_path))

    return layer_paths


def _safe_filename(name: str) -> str:
    safe = re.sub(r"[\\/:*?\"<>|\s]+", "_", name.strip())
    safe = re.sub(r"_+", "_", safe).strip("._")
    if not safe:
        safe = "layer"
    return f"{safe}.md"


def _unique_filename(filename: str, used_names: dict[str, int]) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    count = used_names.get(filename, 0) + 1
    used_names[filename] = count
    if count == 1:
        return filename
    return f"{stem}_{count}{suffix}"


def _render_index(
    project: ProjectSnapshot,
    layer_paths: list[tuple[LayerSnapshot, str]],
    snapshot_path: str | None,
) -> str:
    lines = [
        f"# {project.name}",
        "",
        f"- 工程说明：[工程说明](project.md)",
        f"- Agent 索引：[agent_context.md](agent_context.md)",
        f"- 生成时间：{project.generated_at}",
        f"- 图层数量：{len(project.layers)}",
        "",
    ]
    if snapshot_path:
        lines.extend([f"![当前地图]({snapshot_path})", ""])

    lines.extend(["## 图层卡片", ""])
    for layer, relative_path in layer_paths:
        lines.append(f"- [{layer.name}]({relative_path})")
    lines.append("")
    return "\n".join(lines)


def _render_project(project: ProjectSnapshot, snapshot_path: str | None) -> str:
    lines = [
        f"# 工程说明：{project.name}",
        "",
        f"- 工程文件：{_path_text(project.project_path)}",
        f"- 坐标系：{project.crs}",
        f"- 当前范围：{project.extent}",
        f"- 图层数量：{len(project.layers)}",
        f"- 生成时间：{project.generated_at}",
    ]
    if snapshot_path:
        lines.append(f"- 当前地图截图：{snapshot_path}")
    lines.extend(["", "## 图层清单", ""])
    for layer in project.layers:
        lines.append(f"- {layer.name}（{layer.layer_type}）")
    lines.append("")
    return "\n".join(lines)


def _render_layer(layer: LayerSnapshot) -> str:
    lines = [
        f"# {layer.name}",
        "",
        f"- 类型：{layer.layer_type}",
        f"- 数据源：{_path_text(layer.source)}",
        f"- 坐标系：{layer.crs}",
        f"- 范围：{layer.extent}",
        f"- 有效：{'是' if layer.is_valid else '否'}",
        f"- 可编辑：{'是' if layer.is_editable else '否'}",
    ]
    if layer.feature_count is not None:
        lines.append(f"- 要素数量：{layer.feature_count}")
    if layer.raster_size:
        lines.append(f"- 栅格尺寸：{layer.raster_size}")

    lines.extend(["", "## 字段", ""])
    if layer.fields:
        lines.extend(["| 字段 | 类型 |", "| --- | --- |"])
        for field in layer.fields:
            lines.append(f"| {field.name} | {field.type_name} |")
    else:
        lines.append("无字段信息。")

    lines.extend(
        [
            "",
            "## 用途提示",
            "",
            "这个文件是图层说明卡片。原始数据仍以数据源路径中的文件为准。",
            "",
        ]
    )
    return "\n".join(lines)


def _render_agent_context(
    project: ProjectSnapshot, layer_paths: list[tuple[LayerSnapshot, str]]
) -> str:
    lines = [
        f"# Agent Context: {project.name}",
        "",
        "这是 QGIS 工程的 Markdown 索引，供 agent 快速了解项目上下文。",
        "",
        f"- 工程文件：{_path_text(project.project_path)}",
        f"- 坐标系：{project.crs}",
        f"- 当前范围：{project.extent}",
        "",
        "## 优先读取",
        "",
        "- project.md",
        "- 本文件中列出的图层卡片",
        "",
        "## 图层",
        "",
    ]
    for layer, relative_path in layer_paths:
        lines.append(f"- {layer.name} -> {relative_path}")

    lines.extend(
        [
            "",
            "## 注意",
            "",
            "原始地图数据仍以 QGIS 工程和图层源文件为准，Markdown 只作为说明和索引。",
            "",
        ]
    )
    return "\n".join(lines)


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def _path_text(path: Path | str) -> str:
    return str(path).replace("\\", "/")


def _normalize_markdown_path(path: Path | str) -> str:
    return _path_text(path)
