"""QGIS Agent Notes plugin."""


def classFactory(iface):
    """Load the QGIS plugin instance."""
    from .agent_notes_plugin import AgentNotesPlugin

    return AgentNotesPlugin(iface)
