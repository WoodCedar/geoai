# QGIS Agent Notes

QGIS Agent Notes exports the current QGIS project into Markdown files beside the
saved project file.

It creates:

- `agent_notes/index.md`
- `agent_notes/project.md`
- `agent_notes/agent_context.md`
- `agent_notes/layers/*.md`
- `agent_notes/assets/map_snapshot.png`

Open the generated `agent_notes` folder in Obsidian or any Markdown reader. The
Markdown files are an index and explanation layer only; the original QGIS
project and source datasets remain the authoritative data.

## Usage

1. Save the QGIS project.
2. Open the `Agent Notes` panel.
3. Click `Generate Notes`.
4. Open the generated `agent_notes` folder beside the project file.
