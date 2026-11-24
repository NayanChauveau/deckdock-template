"""Checks on this repo's own deck and documentation."""

import json
import re
from pathlib import Path
from typing import cast

import pytest
from deckdock.format import check_dist

from compiler.builder import build
from compiler.source.load import load_project
from compiler.source.validate import validate_project

REPO = Path(__file__).parents[1]


def test_hello_world_deck_compiles_to_a_valid_dist(tmp_path: Path):
    out = tmp_path / "dist"
    assert build(REPO, out, "test") == []
    assert check_dist(out) == []
    for edition in ("fr", "en"):
        compiled = cast(
            dict[str, dict[str, object]],
            json.loads((out / edition / "deck.json").read_text(encoding="utf-8")),
        )
        assert compiled["deck"]["generator"] == "deck-compiler (deckdock-template)"


@pytest.mark.parametrize("doc", ["AGENTS.md", "CONTENT_GUIDELINES.md", "README.md"])
def test_doc_card_examples_are_valid(tmp_path: Path, doc: str):
    text = (REPO / doc).read_text(encoding="utf-8")
    blocks = cast(list[str], re.findall(r"```yaml\n(.*?)```", text, flags=re.DOTALL))
    assert blocks or doc != "AGENTS.md"
    if not blocks:
        return
    _ = (tmp_path / "deckdock.yaml").write_text(
        "id: test-deck\nname: Test\neditions: [fr, en]\n", encoding="utf-8"
    )
    (tmp_path / "cards").mkdir()
    for i, block in enumerate(blocks):
        _ = (tmp_path / "cards" / f"doc{i}.yaml").write_text(
            "cards:\n" + block, encoding="utf-8"
        )
    project, issues = load_project(tmp_path)
    assert issues == []
    assert project is not None
    assert validate_project(project) == []


@pytest.mark.parametrize("doc", ["AGENTS.md", "README.md"])
def test_docs_state_ids_are_permanent(doc: str):
    text = " ".join((REPO / doc).read_text(encoding="utf-8").split())
    assert "permanent" in text
    assert "review history" in text


@pytest.mark.parametrize(
    "doc", ["AGENTS.md", "README.md", "CONTENT_GUIDELINES.md", "docs/source-format.md"]
)
def test_docs_do_not_mention_removed_commands(doc: str):
    text = (REPO / doc).read_text(encoding="utf-8")
    for removed in ("deckdock init", "deckdock build", "deckdock validate"):
        assert removed not in text
