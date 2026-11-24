import json
import os
from collections.abc import Callable
from pathlib import Path

import pytest

from compiler.source.load import load_project
from compiler.source.models import (
    BasicContent,
    Card,
    ClozeContent,
    McqContent,
    source_json_schema,
)

MakeProject = Callable[[dict[str, str | bytes]], Path]
SCHEMA_PATH = Path(__file__).parents[1] / "schema" / "source.schema.json"
TWO_CARDS = (
    "cards:\n  - id: a-1\n    type: basic\n    front: x\n    back: y\n\n"
    "  - id: a-2\n    type: basic\n    front: x\n    back: y\n"
)


def test_yaml_syntax_error_reports_file_and_line(make_project: MakeProject):
    root = make_project({"cards/a.yaml": "cards:\n  - id: a\n    type: [basic\n"})
    project, issues = load_project(root)
    assert project is None and str(issues[0]).startswith("cards/a.yaml:3: invalid YAML")


def test_card_line_numbers(make_project: MakeProject):
    project, _ = load_project(make_project({"cards/a.yaml": TWO_CARDS}))
    assert project is not None
    assert [c.line for c in project.cards] == [2, 7]


def test_non_mapping_root(make_project: MakeProject):
    _, issues = load_project(make_project({"cards/a.yaml": "- 1\n- 2\n"}))
    assert "cards/a.yaml:1:" in str(issues[0])


def test_empty_file_and_missing_cards_key(make_project: MakeProject):
    _, issues = load_project(
        make_project({"cards/a.yaml": "", "cards/b.yaml": "other: 1\n"})
    )
    assert [str(i)[:13] for i in issues] == ["cards/a.yaml:", "cards/b.yaml:"]


def test_cards_not_a_list_and_item_not_a_mapping(make_project: MakeProject):
    _, issues = load_project(
        make_project({"cards/a.yaml": "cards: 3\n", "cards/b.yaml": "cards:\n  - 1\n"})
    )
    assert "cards/a.yaml:1: 'cards' must be a list" in [str(i) for i in issues]
    assert "cards/b.yaml:2: card must be a mapping" in [str(i) for i in issues]


def test_missing_config_and_no_cards(make_project: MakeProject, tmp_path: Path):
    project, issues = load_project(tmp_path)
    assert project is None
    assert [str(i) for i in issues] == [
        "deckdock.yaml: file not found",
        "cards: no card files found",
    ]
    _, issues = load_project(make_project({}))
    assert [str(i) for i in issues] == ["cards: no card files found"]


def test_config_errors(make_project: MakeProject):
    root = make_project(
        {"deckdock.yaml": "id: x\neditions: []\n", "cards/a.yaml": TWO_CARDS}
    )
    _, issues = load_project(root)
    messages = [str(i) for i in issues]
    assert any(m.startswith("deckdock.yaml: name: Field required") for m in messages)
    assert any(m.startswith("deckdock.yaml: editions:") for m in messages)


def test_duplicate_edition_codes_in_config(make_project: MakeProject):
    root = make_project(
        {
            "deckdock.yaml": "id: x\nname: X\neditions: [fr, fr]\n",
            "cards/a.yaml": TWO_CARDS,
        }
    )
    _, issues = load_project(root)
    assert "duplicate edition 'fr'" in str(issues[0])


def test_invalid_utf8(make_project: MakeProject):
    _, issues = load_project(make_project({"cards/a.yaml": b"cards: \xff\n"}))
    assert str(issues[0]) == "cards/a.yaml: file is not valid UTF-8"


def test_files_sorted_and_yml_included(make_project: MakeProject):
    card = "cards:\n  - id: {id}\n    type: basic\n    front: x\n    back: y\n"
    root = make_project(
        {
            "cards/z.yml": card.format(id="z-1"),
            "cards/b/a.yaml": card.format(id="b-1"),
            "cards/a.yaml": card.format(id="a-1"),
            "cards/notes.txt": "ignored",
        }
    )
    project, issues = load_project(root)
    assert issues == [] and project is not None
    assert [(c.card.id, c.path) for c in project.cards] == [
        ("a-1", "cards/a.yaml"),
        ("b-1", "cards/b/a.yaml"),
        ("z-1", "cards/z.yml"),
    ]


def test_pydantic_errors_have_card_line_and_field_path(make_project: MakeProject):
    text = "cards:\n  - id: hello-001\n    type: basic\n    fr: { front: x }\n    en: { front: x, back: y }\n"
    _, issues = load_project(make_project({"cards/a.yaml": text}))
    assert [str(i) for i in issues] == [
        "cards/a.yaml:2: hello-001.fr.back: Field required"
    ]


def test_direct_content_errors_and_choice_path(make_project: MakeProject):
    text = (
        "cards:\n  - id: a\n    type: basic\n    front: x\n"
        "  - id: b\n    type: mcq\n    question: q\n    choices:\n      - { correct: true }\n"
    )
    _, issues = load_project(make_project({"cards/a.yaml": text}))
    assert [str(i) for i in issues] == [
        "cards/a.yaml:2: a.back: Field required",
        "cards/a.yaml:5: b.choices.0.text: Field required",
    ]


def test_unknown_field_and_bad_type(make_project: MakeProject):
    text = "cards:\n  - id: a\n    type: nope\n    front: x\n  - id: b\n    type: basic\n    front: x\n    back: y\n    bogus: 1\n"
    _, issues = load_project(make_project({"cards/a.yaml": text}))
    messages = [str(i) for i in issues]
    assert any(m.startswith("cards/a.yaml:2: a.type:") for m in messages)
    assert "cards/a.yaml:5: b.bogus: Extra inputs are not permitted" in messages


def test_mix_of_direct_and_per_edition_content_is_rejected_by_model():
    with pytest.raises(ValueError, match="mix of direct and per-edition content"):
        _ = Card.model_validate(
            {
                "id": "a",
                "type": "basic",
                "front": "x",
                "back": "y",
                "fr": {"front": "x", "back": "y"},
            }
        )


def test_content_for_prefers_direct_then_edition():
    direct = Card.model_validate(
        {"id": "a", "type": "basic", "front": "x", "back": "y"}
    )
    assert direct.content_for("de") == BasicContent(front="x", back="y")
    per_edition = Card.model_validate(
        {
            "id": "a",
            "type": "cloze",
            "fr": {"text": "{{c1::a}}"},
            "en": {"text": "{{c1::b}}"},
        }
    )
    assert per_edition.content_for("en") == ClozeContent(text="{{c1::b}}")
    assert per_edition.content_for("de") is None


def test_mcq_content_model():
    card = Card.model_validate(
        {
            "id": "a",
            "type": "mcq",
            "fr": {
                "question": "q",
                "choices": [{"text": "1"}, {"text": "2", "correct": True}],
            },
        }
    )
    content = card.content_for("fr")
    assert isinstance(content, McqContent) and content.choices[1].correct


def test_source_schema_up_to_date():
    assert json.loads(SCHEMA_PATH.read_text(encoding="utf-8")) == source_json_schema()


@pytest.mark.parametrize("code", ["../../escaped", "/tmp/abs", "FR", "a/b", "", "fr\n"])
def test_edition_codes_must_be_slugs(make_project: MakeProject, code: str):
    config = f"id: x\nname: X\neditions: [fr, {json.dumps(code)}]\n"
    _, issues = load_project(
        make_project({"deckdock.yaml": config, "cards/a.yaml": TWO_CARDS})
    )
    assert [str(i) for i in issues] == [
        f"deckdock.yaml: editions: Value error, invalid edition code {code!r} "
        + "(lowercase letters, digits and single dashes)"
    ]


@pytest.mark.parametrize("locked", [".", "cards"])
def test_unreadable_project_is_an_issue(make_project: MakeProject, locked: str):
    root = make_project({"cards/a.yaml": TWO_CARDS})
    target = root / locked
    target.chmod(0)
    try:
        if os.access(target, os.R_OK):
            pytest.skip("permissions are not enforced")
        project, issues = load_project(root)
    finally:
        target.chmod(0o755)
    assert project is None
    assert "cards: cannot read directory: Permission denied" in [str(i) for i in issues]
