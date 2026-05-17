from pathlib import Path

from qgis_agent_notes.core import (
    ExportOptions,
    FieldSnapshot,
    LayerSnapshot,
    ProjectSnapshot,
    write_agent_notes,
)


def _layer(
    name="Roads [draft]",
    source="D:/gis/demo/roads.gpkg|layername=roads",
    fields=None,
    is_valid=True,
    visible=True,
    selected=False,
):
    return LayerSnapshot(
        name=name,
        layer_type="vector",
        source=source,
        crs="EPSG:4326",
        extent="0.000000,0.000000,1.000000,1.000000",
        feature_count=3,
        raster_size=None,
        fields=fields
        if fields is not None
        else [
            FieldSnapshot("name|label", "String", null_count=1, sample_values=["A|B", "[C]"]),
            FieldSnapshot("length", "Real", null_count=0, sample_values=["12.5"]),
        ],
        is_valid=is_valid,
        is_editable=False,
        visible=visible,
        selected=selected,
        group_path=("Base", "Transport"),
    )


def _project(layers=None):
    return ProjectSnapshot(
        name="Demo Project",
        project_path=Path("D:/gis/demo/demo.qgz"),
        crs="EPSG:4326",
        extent="0.000000,0.000000,1.000000,1.000000",
        generated_at="2026-05-17 09:30:00",
        layers=layers if layers is not None else [_layer()],
        qgis_version="4.0.2",
        plugin_version="0.3.0",
    )


def test_030_writes_markdown_workflow_files_and_inventory(tmp_path):
    output_dir = write_agent_notes(
        _project(),
        tmp_path,
        map_snapshot_relative_path=Path("assets/map_snapshot.png"),
        options=ExportOptions(language="en"),
    )

    for name in (
        "index.md",
        "summary.md",
        "project.md",
        "agent_context.md",
        "data_inventory.md",
        "history.md",
        "changes.md",
        "quality_report.md",
        "map_view.md",
        "agent_prompt.md",
    ):
        assert (output_dir / name).exists(), name

    index_text = (output_dir / "index.md").read_text(encoding="utf-8")
    assert "[Summary](summary.md)" in index_text
    assert "[Data inventory](data_inventory.md)" in index_text
    assert "[Quality report](quality_report.md)" in index_text
    assert "![Current map](assets/map_snapshot.png)" in index_text

    inventory = (output_dir / "data_inventory.md").read_text(encoding="utf-8")
    assert "| Roads \\[draft\\] | vector | Base / Transport | EPSG:4326 | 3 |" in inventory
    assert "roads.gpkg" in inventory

    field_table = (output_dir / "layers" / "Roads_draft.md").read_text(encoding="utf-8")
    assert "| name\\|label | String | 1 | A\\|B; \\[C\\] |" in field_table
    assert "[source](D:/gis/demo/roads.gpkg)" in field_table


def test_030_cleans_stale_layer_cards_and_tracks_changes(tmp_path):
    output_dir = write_agent_notes(
        _project([_layer(name="Old layer", source="D:/gis/old.geojson")]),
        tmp_path,
        options=ExportOptions(language="en"),
    )
    assert (output_dir / "layers" / "Old_layer.md").exists()

    write_agent_notes(
        _project([_layer(name="New layer", source="D:/gis/new.geojson")]),
        tmp_path,
        options=ExportOptions(language="en", clean_stale=True),
    )

    assert not (output_dir / "layers" / "Old_layer.md").exists()
    assert (output_dir / "layers" / "New_layer.md").exists()
    changes = (output_dir / "changes.md").read_text(encoding="utf-8")
    assert "Added layers" in changes
    assert "New layer" in changes
    assert "Removed layers" in changes
    assert "Old layer" in changes


def test_030_reports_quality_issues_and_skips_broken_snapshot_link(tmp_path):
    output_dir = write_agent_notes(
        _project(
            [
                _layer(name="Valid layer"),
                _layer(name="Broken layer", source="", is_valid=False),
            ]
        ),
        tmp_path,
        map_snapshot_relative_path=None,
        options=ExportOptions(language="en"),
    )

    index_text = (output_dir / "index.md").read_text(encoding="utf-8")
    assert "![Current map]" not in index_text

    quality = (output_dir / "quality_report.md").read_text(encoding="utf-8")
    assert "Invalid layers" in quality
    assert "Broken layer" in quality
    assert "Missing data sources" in quality


def test_030_supports_visible_and_selected_layer_scope(tmp_path):
    layers = [
        _layer(name="Visible selected", visible=True, selected=True),
        _layer(name="Hidden selected", visible=False, selected=True),
        _layer(name="Visible unselected", visible=True, selected=False),
    ]

    visible_output = write_agent_notes(
        _project(layers),
        tmp_path / "visible",
        options=ExportOptions(language="en", layer_scope="visible"),
    )
    visible_inventory = (visible_output / "data_inventory.md").read_text(encoding="utf-8")
    assert "Visible selected" in visible_inventory
    assert "Visible unselected" in visible_inventory
    assert "Hidden selected" not in visible_inventory

    selected_output = write_agent_notes(
        _project(layers),
        tmp_path / "selected",
        options=ExportOptions(language="en", layer_scope="selected"),
    )
    selected_inventory = (selected_output / "data_inventory.md").read_text(encoding="utf-8")
    assert "Visible selected" in selected_inventory
    assert "Hidden selected" in selected_inventory
    assert "Visible unselected" not in selected_inventory
