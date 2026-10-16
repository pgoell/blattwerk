from pathlib import Path

TUTORIAL = (
    Path(__file__).resolve().parent.parent / "docs/okf/tutorials/dein-erstes-blatt-mit-claude.md"
)


def test_tutorial_walks_through_the_extension_install():
    text = TUTORIAL.read_text(encoding="utf-8")
    for word in ("blattomat.mcpb", "API-Schlüssel", "Erweiterung"):
        assert word in text


def test_tutorial_has_no_expert_config():
    text = TUTORIAL.read_text(encoding="utf-8")
    assert "Technikwissen" not in text
    assert "mcpServers" not in text
