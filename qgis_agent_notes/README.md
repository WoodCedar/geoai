# QGIS Agent Notes

QGIS Agent Notes exports the current QGIS project into Markdown files beside the
saved project file.

It creates:

- `agent_notes/index.md`
- `agent_notes/summary.md`
- `agent_notes/project.md`
- `agent_notes/agent_context.md`
- `agent_notes/agent_prompt.md`
- `agent_notes/data_inventory.md`
- `agent_notes/quality_report.md`
- `agent_notes/changes.md`
- `agent_notes/history.md`
- `agent_notes/map_view.md`
- `agent_notes/layers/*.md`
- `agent_notes/assets/map_snapshot.png`

Open the generated `agent_notes` folder in any Markdown reader. The Markdown
files are an index and explanation layer only; the original QGIS project and
source datasets remain the authoritative data.

## Usage

1. Save the QGIS project.
2. Open the `Agent Notes` panel.
3. Choose all layers, visible layers, or selected layers.
4. Choose Chinese or English Markdown output.
5. Click `Generate Notes`.
6. Open the generated `agent_notes` folder beside the project file.
