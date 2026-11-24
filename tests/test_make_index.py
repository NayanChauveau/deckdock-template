import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

from compiler.builder import build
from scripts.make_index import main, make_index

MakeProject = Callable[[dict[str, str | bytes]], Path]

CARDS = """\
cards:
  - id: hello-001
    type: basic
    fr: {front: Bonjour, back: Salut}
    en: {front: Hello, back: Hi}
"""


def test_make_index_lists_editions_sorted(make_project: MakeProject, tmp_path: Path):
    root = make_project(
        {
            "cards/a.yaml": CARDS,
            "deckdock.yaml": "id: test-deck\nname: Test\neditions: [fr, en]\n",
        }
    )
    dist = tmp_path / "dist"
    assert build(root, dist, "v1") == []
    assert make_index(dist) == {
        "format": "deckdock-index/1",
        "editions": [
            {"edition": "en", "name": "Test", "language": ["en"], "version": "v1"},
            {"edition": "fr", "name": "Test", "language": ["fr"], "version": "v1"},
        ],
    }


def test_main_writes_index_json(make_project: MakeProject, tmp_path: Path):
    root = make_project({"cards/a.yaml": CARDS})
    dist = tmp_path / "dist"
    assert build(root, dist, "v1") == []
    assert main([str(dist)]) == 0
    data = cast(
        dict[str, object],
        json.loads((dist / "index.json").read_text(encoding="utf-8")),
    )
    assert data["format"] == "deckdock-index/1"
    editions = cast(list[dict[str, object]], data["editions"])
    assert [entry["edition"] for entry in editions] == ["en", "fr"]
