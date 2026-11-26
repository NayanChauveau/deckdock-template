# pyright: reportAny=false, reportExplicitAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false
"""Pydantic models of the YAML source (deckdock.yaml and cards/*.yaml)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Literal, cast

from deckdock.format import SLUG_RE
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic.json_schema import models_json_schema
from pydantic_core import InitErrorDetails, PydanticCustomError

CardType = Literal["basic", "reversed", "cloze", "mcq"]


class DeckOptions(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    new_per_day: int | None = Field(default=None, ge=0)
    reviews_per_day: int | None = Field(default=None, ge=0)


class ProjectConfig(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    id: str
    name: str | dict[str, str]
    description: str | dict[str, str] | None = None
    icon: str | None = None
    editions: list[str] = Field(min_length=1)
    license: str | None = None
    homepage: str | None = None
    options: DeckOptions | None = None

    @field_validator("editions")
    @classmethod
    def _check_editions(cls, value: list[str]) -> list[str]:
        seen: set[str] = set()
        for code in value:
            if not SLUG_RE.fullmatch(code):
                raise ValueError(
                    f"invalid edition code {code!r} (lowercase letters, digits and single dashes)"
                )
            if code in seen:
                raise ValueError(f"duplicate edition '{code}'")
            seen.add(code)
        return value


class BasicContent(BaseModel):
    """Content of a `basic` or `reversed` card."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    front: str
    back: str


class ClozeContent(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    text: str
    extra: str = ""


class Choice(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    text: str
    correct: bool = False


class McqContent(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    question: str
    choices: list[Choice]
    explanation: str = ""


Content = BasicContent | ClozeContent | McqContent

_CONTENT_MODELS: dict[str, type[BaseModel]] = {
    "basic": BasicContent,
    "reversed": BasicContent,
    "cloze": ClozeContent,
    "mcq": McqContent,
}
_BASE_KEYS = frozenset({"id", "type", "deck", "tags", "status"})
_EDITION_CONTENT = [
    {"$ref": "#/$defs/BasicContent"},
    {"$ref": "#/$defs/ClozeContent"},
    {"$ref": "#/$defs/McqContent"},
]


def _card_json_schema(schema: dict[str, Any]) -> None:
    """Describe the card as written in YAML (flat content or per-edition blocks)."""
    properties = cast(dict[str, Any], schema["properties"])
    _ = properties.pop("direct", None)
    _ = properties.pop("editions", None)
    for model in (BasicContent, ClozeContent, McqContent):
        for name, prop in cast(
            dict[str, Any], model.model_json_schema()["properties"]
        ).items():
            properties.setdefault(name, prop)
    schema["required"] = ["id", "type"]
    schema["additionalProperties"] = {"anyOf": _EDITION_CONTENT}


class Card(BaseModel):
    """A card. Content is either direct (same for all editions) or per edition.

    In YAML, content keys of the card's type (e.g. `front`) give direct content;
    any other mapping-valued key is an edition block (`fr: {front: ...}`).
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(
        extra="forbid", json_schema_extra=_card_json_schema
    )

    id: str
    type: CardType
    deck: str = ""
    tags: list[str] = []
    status: Literal["draft", "reviewed"] = "reviewed"
    direct: Content | None = None
    editions: dict[str, Content] = {}

    @model_validator(mode="before")
    @classmethod
    def _split_content(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        raw = cast(dict[Any, Any], data)
        out = {k: v for k, v in raw.items() if k in _BASE_KEYS}
        rest = {k: v for k, v in raw.items() if k not in _BASE_KEYS}
        card_type = raw.get("type")
        model = _CONTENT_MODELS.get(card_type) if isinstance(card_type, str) else None
        if model is None:  # the invalid type is reported on its own
            return out
        fields = set(model.model_fields)
        direct = {k: v for k, v in rest.items() if k in fields}
        blocks = {
            k: v
            for k, v in rest.items()
            if k not in fields and isinstance(k, str) and isinstance(v, dict)
        }
        out.update(
            {k: v for k, v in rest.items() if k not in direct and k not in blocks}
        )
        errors: list[tuple[tuple[str, ...], str]] = []
        if direct and blocks:
            errors.append(((), "mix of direct and per-edition content"))
        else:
            if direct:
                out["direct"], found = _parse(model, direct, ())
                errors.extend(found)
            if blocks:
                parsed: dict[str, Any] = {}
                for edition, block in blocks.items():
                    parsed[edition], found = _parse(model, block, (edition,))
                    errors.extend(found)
                out["editions"] = parsed
        if errors:
            raise ValidationError.from_exception_data(
                "Card",
                [
                    InitErrorDetails(
                        type=PydanticCustomError("card_content", "{msg}", {"msg": msg}),
                        loc=loc,
                        input=None,
                    )
                    for loc, msg in errors
                ],
            )
        return out

    def content_for(self, edition: str) -> Content | None:
        """Direct content if present, else the edition's block, else None."""
        if self.direct is not None:
            return self.direct
        return self.editions.get(edition)


def _parse(
    model: type[BaseModel], value: Any, prefix: tuple[str, ...]
) -> tuple[BaseModel | None, list[tuple[tuple[str, ...], str]]]:
    try:
        return model.model_validate(value), []
    except ValidationError as exc:
        return None, [
            (prefix + tuple(str(p) for p in e["loc"]), e["msg"]) for e in exc.errors()
        ]


class CardFile(BaseModel):
    """The content of one cards/*.yaml file."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    cards: list[Card]


@dataclass(frozen=True)
class LoadedCard:
    card: Card
    path: str
    line: int


@dataclass(frozen=True)
class Project:
    root: Path
    config: ProjectConfig
    cards: list[LoadedCard]


def source_json_schema() -> dict[str, Any]:
    """JSON Schema of deckdock.yaml and of cards files, for editor support."""
    _, defs = models_json_schema(
        [(ProjectConfig, "validation"), (CardFile, "validation")],
        ref_template="#/$defs/{model}",
    )
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "deckdock source",
        "description": "A deckdock.yaml project file or a cards/*.yaml file.",
        "anyOf": [{"$ref": "#/$defs/ProjectConfig"}, {"$ref": "#/$defs/CardFile"}],
        **defs,
    }
