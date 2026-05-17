from pathlib import Path

from qgis_agent_notes.core import (
    FieldSnapshot,
    LayerSnapshot,
    ProjectSnapshot,
    write_agent_notes,
)


def test_write_agent_notes_creates_project_index_layer_cards_and_agent_context(tmp_path):
    project = ProjectSnapshot(
        name="Lake Survey",
        project_path=Path("D:/gis/lake/lake.qgz"),
        crs="EPSG:4490",
        extent="120.100000,30.100000,120.900000,30.900000",
        generated_at="2026-05-17 10:30:00",
        layers=[
            LayerSnapshot(
                name="湖泊 边界",
                layer_type="vector",
                source=Path("D:/gis/lake/data/lake_boundary.gpkg"),
                crs="EPSG:4490",
                extent="120.100000,30.100000,120.900000,30.900000",
                feature_count=12,
                raster_size=None,
                fields=[
                    FieldSnapshot("name", "String"),
                    FieldSnapshot("area", "Real"),
                ],
                is_valid=True,
                is_editable=False,
            ),
            LayerSnapshot(
                name="Sentinel image",
                layer_type="raster",
                source=Path("D:/gis/lake/data/sentinel.tif"),
                crs="EPSG:32651",
                extent="120.000000,30.000000,121.000000,31.000000",
                feature_count=None,
                raster_size="10980 x 10980",
                fields=[],
                is_valid=True,
                is_editable=False,
            ),
        ],
    )

    output_dir = write_agent_notes(
        project,
        tmp_path,
        map_snapshot_relative_path=Path("assets/map_snapshot.png"),
    )

    assert output_dir == tmp_path / "agent_notes"
    for name in (
        "index.md",
        "summary.md",
        "project.md",
        "agent_context.md",
        "data_inventory.md",
        "quality_report.md",
    ):
        assert (output_dir / name).exists()
    assert (output_dir / "layers" / "湖泊_边界.md").exists()
    assert (output_dir / "layers" / "Sentinel_image.md").exists()

    index_text = (output_dir / "index.md").read_text(encoding="utf-8")
    assert "# Lake Survey" in index_text
    assert "[Project](project.md)" in index_text
    assert "[Data inventory](data_inventory.md)" in index_text
    assert "![当前地图](assets/map_snapshot.png)" in index_text
    assert "[湖泊 边界](layers/湖泊_边界.md)" in index_text

    layer_text = (output_dir / "layers" / "湖泊_边界.md").read_text(encoding="utf-8")
    assert "# 湖泊 边界" in layer_text
    assert "类型: vector" in layer_text
    assert "要素数量: 12" in layer_text
    assert "| name | String |" in layer_text
    assert "D:/gis/lake/data/lake_boundary.gpkg" in layer_text

    agent_text = (output_dir / "agent_context.md").read_text(encoding="utf-8")
    assert "这是给 agent 快速读取的 Markdown 入口" in agent_text
    assert "湖泊 边界 -> layers/湖泊_边界.md" in agent_text
    assert "原始数据和 QGIS 工程才是准确信息来源" in agent_text


def test_write_agent_notes_uses_unique_layer_card_names(tmp_path):
    project = ProjectSnapshot(
        name="Duplicate Names",
        project_path=Path("D:/gis/test.qgz"),
        crs="EPSG:4326",
        extent="0.000000,0.000000,1.000000,1.000000",
        generated_at="2026-05-17 10:30:00",
        layers=[
            LayerSnapshot(
                name="Layer A",
                layer_type="vector",
                source=Path("D:/gis/a.geojson"),
                crs="EPSG:4326",
                extent="0.000000,0.000000,1.000000,1.000000",
                feature_count=1,
                raster_size=None,
                fields=[],
                is_valid=True,
                is_editable=False,
            ),
            LayerSnapshot(
                name="Layer/A",
                layer_type="vector",
                source=Path("D:/gis/b.geojson"),
                crs="EPSG:4326",
                extent="0.000000,0.000000,1.000000,1.000000",
                feature_count=1,
                raster_size=None,
                fields=[],
                is_valid=True,
                is_editable=False,
            ),
        ],
    )

    output_dir = write_agent_notes(project, tmp_path)

    assert (output_dir / "layers" / "Layer_A.md").exists()
    assert (output_dir / "layers" / "Layer_A_2.md").exists()
