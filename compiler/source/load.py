# pyright: reportAny=false, reportExplicitAny=false, reportUnknownVariableType=false, reportUnknownMemberType=false
"""Read deckdock.yaml and cards/**/*.yaml, keeping line numbers for error messages."""

import stat
from pathlib import Path
from typing import Any, cast

import yaml
from deckdock.issues import Issue
from pydantic import ValidationError

from compiler.source.models import Card, LoadedCard, Project, ProjectConfig

CONFIG_FILE = "deckdock.yaml"
CARDS_DIR = "cards"


def load_project(root: Path) -> tuple[Project | None, list[Issue]]:
    """Load a project; the project is None when any issue was found."""
    issues: list[Issue] = []
    config = _load_config(root, issues)
    cards: list[LoadedCard] = []
    unreadable = len(issues)
    files = _card_files(root, issues)
    if not files and len(issues) == unreadable:
        issues.append(Issue(CARDS_DIR, "no card files found"))
    for rel in files:
        cards.extend(_load_cards_file(root, rel, issues))
    if issues or config is None:
        return None, issues
    return Project(root=root, config=config, cards=cards), issues


def _card_files(root: Path, issues: list[Issue]) -> list[str]:
    base = root / CARDS_DIR
    errors: list[OSError] = []
    try:
        # Path.is_dir() hides permission errors on some platforms; stat() surfaces them.
        try:
            if not stat.S_ISDIR(base.stat().st_mode):
                return []
        except FileNotFoundError:
            return []
        found = [
            folder / name
            for folder, _, names in base.walk(on_error=errors.append)
            for name in names
            if name.endswith((".yaml", ".yml")) and (folder / name).is_file()
        ]
    except OSError as exc:
        errors.append(exc)
        found = []
    for exc in errors:
        issues.append(
            Issue(_display(root, exc), f"cannot read directory: {exc.strerror or exc}")
        )
    return sorted(p.relative_to(root).as_posix() for p in found)


def _display(root: Path, exc: OSError) -> str:
    filename = cast(object, exc.filename)
    if not isinstance(filename, str):
        return CARDS_DIR
    try:
        return Path(filename).relative_to(root).as_posix()
    except ValueError:
        return filename


def _yaml_issue(rel: str, exc: yaml.YAMLError) -> Issue:
    mark = cast(
        yaml.Mark | None,
        getattr(exc, "context_mark", None) or getattr(exc, "problem_mark", None),
    )
    problem = cast(str | None, getattr(exc, "problem", None)) or str(exc)
    return Issue(rel, f"invalid YAML: {problem}", mark.line + 1 if mark else None)


def _read_text(root: Path, rel: str, issues: list[Issue]) -> str | None:
    try:
        return (root / rel).read_text(encoding="utf-8")
    except FileNotFoundError:
        issues.append(Issue(rel, "file not found"))
    except UnicodeDecodeError:
        issues.append(Issue(rel, "file is not valid UTF-8"))
    except OSError as exc:
        issues.append(Issue(rel, f"cannot read file: {exc.strerror or exc}"))
    return None


def _load_config(root: Path, issues: list[Issue]) -> ProjectConfig | None:
    text = _read_text(root, CONFIG_FILE, issues)
    if text is None:
        return None
    try:
        data = cast(object, yaml.safe_load(text))
    except yaml.YAMLError as exc:
        issues.append(_yaml_issue(CONFIG_FILE, exc))
        return None
    if not isinstance(data, dict):
        issues.append(Issue(CONFIG_FILE, "must be a mapping", 1))
        return None
    try:
        return ProjectConfig.model_validate(data)
    except ValidationError as exc:
        issues.extend(
            Issue(CONFIG_FILE, _describe(err["loc"], err["msg"]))
            for err in exc.errors()
        )
        return None


def _describe(loc: tuple[int | str, ...], msg: str) -> str:
    prefix = ".".join(str(p) for p in loc)
    return f"{prefix}: {msg}" if prefix else msg


def _load_cards_file(root: Path, rel: str, issues: list[Issue]) -> list[LoadedCard]:
    text = _read_text(root, rel, issues)
    if text is None:
        return []
    try:
        node = yaml.compose(text)
        data = cast(object, yaml.safe_load(text))
    except yaml.YAMLError as exc:
        issues.append(_yaml_issue(rel, exc))
        return []
    if not isinstance(data, dict) or not isinstance(node, yaml.MappingNode):
        issues.append(Issue(rel, "must be a mapping with a 'cards' list", 1))
        return []
    root_map = cast(dict[str, Any], data)
    cards_node = next((v for k, v in node.value if k.value == "cards"), None)
    if not isinstance(root_map.get("cards"), list) or not isinstance(
        cards_node, yaml.SequenceNode
    ):
        issues.append(Issue(rel, "'cards' must be a list", node.start_mark.line + 1))
        return []
    loaded: list[LoadedCard] = []
    for index, (item, item_node) in enumerate(
        zip(cast(list[Any], root_map["cards"]), cards_node.value, strict=True)
    ):
        line = item_node.start_mark.line + 1
        if not isinstance(item, dict):
            issues.append(Issue(rel, "card must be a mapping", line))
            continue
        raw_id = cast(dict[str, Any], item).get("id")
        label = raw_id if isinstance(raw_id, str) and raw_id else f"card #{index + 1}"
        try:
            card = Card.model_validate(item)
        except ValidationError as exc:
            issues.extend(
                Issue(rel, _describe((label, *err["loc"]), err["msg"]), line)
                for err in exc.errors()
            )
            continue
        loaded.append(LoadedCard(card=card, path=rel, line=line))
    return loaded
