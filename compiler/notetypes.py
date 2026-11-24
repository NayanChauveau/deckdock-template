"""The four built-in DeckDock notetypes, read from package-data template files."""

from importlib.resources import files
from typing import Literal, TypedDict

from deckdock.format import Notetype, Template

LABELS: dict[str, dict[str, str]] = {
    "en": {"explanation": "Explanation"},
    "fr": {"explanation": "Explication"},
}


class _Spec(TypedDict):
    name: str
    kind: Literal["standard", "cloze"]
    fields: list[str]
    templates: list[tuple[str, str]]  # (front file, back file), without ".html"


_SPECS: dict[str, _Spec] = {
    "basic": {
        "name": "DeckDock Basic",
        "kind": "standard",
        "fields": ["Front", "Back"],
        "templates": [("basic.front", "basic.back")],
    },
    "reversed": {
        "name": "DeckDock Basic (and reversed)",
        "kind": "standard",
        "fields": ["Front", "Back"],
        "templates": [
            ("basic.front", "basic.back"),
            ("reversed.front2", "reversed.back2"),
        ],
    },
    "cloze": {
        "name": "DeckDock Cloze",
        "kind": "cloze",
        "fields": ["Text", "Extra"],
        "templates": [("cloze.front", "cloze.back")],
    },
    "mcq": {
        "name": "DeckDock MCQ",
        "kind": "standard",
        "fields": ["Question", "Choices", "Explanation"],
        "templates": [("mcq.front", "mcq.back")],
    },
}


def _read(name: str) -> str:
    return (files("compiler") / "notetypes" / name).read_text(encoding="utf-8")


def _render(name: str, labels: dict[str, str]) -> str:
    text = _read(name)
    text = text.replace("__MCQ_JS__", _read("mcq.js").strip())
    return text.replace("__LABEL_EXPLANATION__", labels["explanation"])


def notetype_for(card_type: str, edition: str) -> Notetype:
    """Return the compiled notetype for a card type, with labels localised for `edition`."""
    spec = _SPECS[card_type]
    labels = LABELS.get(edition, LABELS["en"])
    templates: list[Template] = [
        {
            "name": f"Card {index}",
            "front": _render(f"{front}.html", labels),
            "back": _render(f"{back}.html", labels),
        }
        for index, (front, back) in enumerate(spec["templates"], start=1)
    ]
    return {
        "id": card_type,
        "name": spec["name"],
        "kind": spec["kind"],
        "fields": list(spec["fields"]),
        "templates": templates,
        "css": _read("base.css"),
    }
