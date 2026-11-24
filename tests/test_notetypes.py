import re
from typing import cast

import pytest
from deckdock.format import Notetype, Template, check_deck

from compiler.notetypes import notetype_for

TABLE = [
    ("basic", "DeckDock Basic", "standard", ["Front", "Back"], 1),
    ("reversed", "DeckDock Basic (and reversed)", "standard", ["Front", "Back"], 2),
    ("cloze", "DeckDock Cloze", "cloze", ["Text", "Extra"], 1),
    ("mcq", "DeckDock MCQ", "standard", ["Question", "Choices", "Explanation"], 1),
]
FIELD_REF = re.compile(r"\{\{\s*(?:[#^/]\s*)?(?:cloze:)?([^{}:]+?)\s*\}\}")


def templates_of(notetype: Notetype) -> list[Template]:
    return notetype["templates"]


@pytest.mark.parametrize(("card_type", "name", "kind", "fields", "count"), TABLE)
def test_table_values(
    card_type: str, name: str, kind: str, fields: list[str], count: int
):
    notetype = notetype_for(card_type, "en")
    assert notetype["id"] == card_type
    assert notetype["name"] == name
    assert notetype["kind"] == kind
    assert notetype["fields"] == fields
    assert len(templates_of(notetype)) == count
    assert "anki_id" not in notetype
    assert notetype["css"]


@pytest.mark.parametrize("card_type", [row[0] for row in TABLE])
def test_templates_reference_only_declared_fields(card_type: str):
    notetype = notetype_for(card_type, "en")
    declared = notetype["fields"]
    for template in templates_of(notetype):
        for side in (template["front"], template["back"]):
            found = cast(list[str], FIELD_REF.findall(side))
            refs = {ref for ref in found if ref != "FrontSide"}
            assert refs, side
            assert refs <= set(declared), refs - set(declared)
    assert "{{cloze:Text}}" in templates_of(notetype_for("cloze", "en"))[0]["front"]
    assert "{{cloze:Text}}" in templates_of(notetype_for("cloze", "en"))[0]["back"]


def test_mcq_includes_shuffle_script_on_both_sides():
    template = templates_of(notetype_for("mcq", "en"))[0]
    for side in (template["front"], template["back"]):
        assert "deckdock-mcq:" in side
        assert "sessionStorage" in side
        assert "__MCQ_JS__" not in side
    assert "dd-correct" in template["back"]


def test_labels_localised():
    def back(edition: str) -> str:
        return templates_of(notetype_for("mcq", edition))[0]["back"]

    assert ">Explication<" in back("fr")
    assert ">Explanation<" not in back("fr")
    assert ">Explanation<" in back("en")
    assert ">Explanation<" in back("de")
    assert "__LABEL" not in back("de")


@pytest.mark.parametrize("card_type", [row[0] for row in TABLE])
def test_output_passes_check_deck(card_type: str):
    notetype = notetype_for(card_type, "en")
    fields = {name: "<p>x</p>" for name in notetype["fields"]}
    data: dict[str, object] = {
        "format": "deckdock/1",
        "deck": {
            "id": "t",
            "edition": "en",
            "name": "T",
            "language": ["en"],
            "version": "dev",
        },
        "notetypes": [notetype],
        "notes": [
            {
                "guid": "abc123",
                "notetype": card_type,
                "deck": "",
                "fields": fields,
                "tags": [],
            }
        ],
        "media": [],
    }
    assert check_deck(data, strict=True) == []
