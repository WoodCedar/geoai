from configparser import ConfigParser
from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parents[1] / "qgis_agent_notes"


def test_plugin_package_has_required_repository_files():
    assert (PLUGIN_DIR / "__init__.py").exists()
    assert (PLUGIN_DIR / "metadata.txt").exists()
    assert (PLUGIN_DIR / "LICENSE").exists()
    assert (PLUGIN_DIR / "README.md").exists()


def test_plugin_metadata_has_publish_required_values():
    parser = ConfigParser()
    parser.read(PLUGIN_DIR / "metadata.txt", encoding="utf-8")
    metadata = parser["general"]

    for key in (
        "name",
        "qgisMinimumVersion",
        "description",
        "about",
        "version",
        "author",
        "email",
        "repository",
        "tracker",
        "homepage",
    ):
        assert metadata.get(key, "").strip(), f"metadata {key} must be set"

    assert metadata["repository"].startswith("https://github.com/")
    assert metadata["tracker"].startswith("https://github.com/")
    assert metadata["homepage"].startswith("https://github.com/")
    assert "plugin" not in PLUGIN_DIR.name.lower()


def test_plugin_metadata_version_is_030():
    parser = ConfigParser()
    parser.read(PLUGIN_DIR / "metadata.txt", encoding="utf-8")

    assert parser["general"]["version"] == "0.3.0"
    assert "0.3.0" in parser["general"].get("changelog", "")
