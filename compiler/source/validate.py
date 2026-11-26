"""Business rules for a loaded project."""

import re
from collections.abc import Iterator

from deckdock.format import SLUG_RE
from deckdock.format.emoji import is_single_emoji
from deckdock.issues import Issue

from compiler.media import media_problem
from compiler.render.markdown import render
from compiler.source.load import CONFIG_FILE
from compiler.source.models import (
    BasicContent,
    Card,
    ClozeContent,
    Content,
    McqContent,
    Project,
)

_CLOZE = re.compile(r"\{\{c\d+::.+?\}\}", re.DOTALL)


def validate_project(project: Project) -> list[Issue]:
    issues = _validate_config(project)
    seen: dict[str, str] = {}
    for loaded in project.cards:
        card, path, line = loaded.card, loaded.path, loaded.line
        here = f"{path}:{line}"

        def add(message: str, *, _path: str = path, _line: int = line) -> None:
            issues.append(Issue(_path, message, _line))

        if not SLUG_RE.fullmatch(card.id):
            add(f"invalid card id {card.id!r}")
        if card.id in seen:
            add(f"duplicate card id '{card.id}' (also at {seen[card.id]})")
        else:
            seen[card.id] = here
        if card.deck and any(not seg.strip() for seg in card.deck.split("::")):
            add(f"empty segment in deck path {card.deck!r}")
        for edition in card.editions:
            if edition not in project.config.editions:
                add(f"unknown edition '{edition}'")
        if card.direct is None and not card.editions:
            add("no content for any edition")
        for edition, content in _contents(card):
            suffix = f" (edition '{edition}')" if edition else ""
            for message in _content_issues(content, project):
                add(message + suffix)
    return issues


def _contents(card: Card) -> Iterator[tuple[str | None, Content]]:
    if card.direct is not None:
        yield None, card.direct
    yield from card.editions.items()


def _validate_config(project: Project) -> list[Issue]:
    config = project.config
    issues: list[Issue] = []
    if not SLUG_RE.fullmatch(config.id):
        issues.append(Issue(CONFIG_FILE, f"invalid project id {config.id!r}"))
    if config.icon is not None and not is_single_emoji(config.icon):
        issues.append(Issue(CONFIG_FILE, "icon must be a single emoji"))
    for field, value in (("name", config.name), ("description", config.description)):
        if isinstance(value, dict):
            issues.extend(
                Issue(CONFIG_FILE, f"missing {field} for edition '{edition}'")
                for edition in config.editions
                if edition not in value
            )
    return issues


def _content_issues(content: Content, project: Project) -> list[str]:
    messages: list[str] = []
    if isinstance(content, ClozeContent) and not _CLOZE.search(content.text):
        messages.append("cloze text has no deletion")
    if isinstance(content, McqContent):
        correct = sum(1 for choice in content.choices if choice.correct)
        if len(content.choices) < 2 or correct != 1:
            messages.append(
                "mcq must have at least 2 choices and exactly one correct choice"
            )
    for ref in _media_refs(content):
        problem = media_problem(project.root, ref)
        if problem is not None:
            messages.append(problem)
    return messages


def _texts(content: Content) -> list[str]:
    if isinstance(content, BasicContent):
        return [content.front, content.back]
    if isinstance(content, ClozeContent):
        return [content.text, content.extra]
    return [content.question, content.explanation, *(c.text for c in content.choices)]


def _media_refs(content: Content) -> list[str]:
    """Local references, collected by the same renderer the builder uses."""
    refs: set[str] = set()
    for text in _texts(content):
        refs |= render(text)[1]
    return sorted(refs)
