import json
import os
from collections.abc import Callable
from hashlib import sha256
from pathlib import Path
from typing import cast

import pytest
from deckdock.format import check_dist
from deckdock.guid import card_guid
from deckdock.issues import Issue

from compiler.builder import build, compile_edition
from compiler.cli import main
from compiler.source.load import load_project
from compiler.source.models import Project

MakeProject = Callable[[dict[str, str | bytes]], Path]

CARDS = """\
cards:
  - id: hello-001
    type: basic
    fr: {front: Bonjour, back: Salut}
    en: {front: Hello, back: Hi}
  - id: fr-only
    type: basic
    deck: Sub::Deep
    tags: [t1]
    fr: {front: "Côte-d’Or <b>&</b>", back: Bourgogne}
  - id: draft-001
    type: basic
    status: draft
    front: Draft
    back: Draft
"""


def _read(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _notes(path: Path) -> list[dict[str, object]]:
    return cast(list[dict[str, object]], _read(path)["notes"])


def test_build_two_editions_layout(make_project: MakeProject, tmp_path: Path):
    root = make_project({"cards/a.yaml": CARDS})
    out = tmp_path / "out"
    assert build(root, out, "v1") == []
    assert (out / "fr" / "deck.json").is_file()
    assert (out / "en" / "deck.json").is_file()
    assert check_dist(out) == []
    deck = cast(dict[str, object], _read(out / "fr" / "deck.json")["deck"])
    assert deck["language"] == ["fr"]
    assert deck["version"] == "v1"
    assert list(deck)[:2] == ["id", "edition"]


def test_guid_matches_card_guid(make_project: MakeProject, tmp_path: Path):
    root = make_project({"cards/a.yaml": CARDS})
    out = tmp_path / "out"
    assert build(root, out, "v") == []
    guids = {n["guid"] for n in _notes(out / "fr" / "deck.json")}
    assert card_guid("test-deck", "hello-001", "fr") in guids


def test_card_missing_language_is_omitted_from_that_edition(
    make_project: MakeProject, tmp_path: Path
):
    root = make_project({"cards/a.yaml": CARDS})
    out = tmp_path / "out"
    assert build(root, out, "v") == []
    assert len(_notes(out / "fr" / "deck.json")) == 2
    assert len(_notes(out / "en" / "deck.json")) == 1


def test_empty_edition_fails(make_project: MakeProject, tmp_path: Path):
    cards = "cards:\n  - id: a\n    type: basic\n    fr: {front: A, back: B}\n"
    root = make_project({"cards/a.yaml": cards})
    out = tmp_path / "out"
    issues = build(root, out, "v")
    assert [str(i) for i in issues] == ["deckdock.yaml: edition 'en' has no cards"]
    assert not out.exists()


def test_drafts_excluded(make_project: MakeProject, tmp_path: Path):
    root = make_project({"cards/a.yaml": CARDS})
    out = tmp_path / "out"
    assert build(root, out, "v") == []
    text = (out / "fr" / "deck.json").read_text(encoding="utf-8")
    assert "Draft" not in text
    assert card_guid("test-deck", "draft-001", "fr") not in text


def test_accents_and_html_preserved_utf8(make_project: MakeProject, tmp_path: Path):
    root = make_project({"cards/a.yaml": CARDS})
    out = tmp_path / "out"
    assert build(root, out, "v") == []
    raw = (out / "fr" / "deck.json").read_bytes().decode("utf-8")
    assert "Côte-d’Or" in raw
    assert "\\u00f4" not in raw
    assert "<b>&amp;</b>" in raw
    assert raw.endswith("}\n")


def test_media_copied_with_sha_and_size(make_project: MakeProject, tmp_path: Path):
    data = b"\x89PNGdata"
    cards = "cards:\n  - id: a\n    type: basic\n    front: '![x](media/pic.png)'\n    back: B\n"
    root = make_project(
        {"cards/a.yaml": cards, "media/pic.png": data, "media/unused.png": b"zz"}
    )
    out = tmp_path / "out"
    assert build(root, out, "v") == []
    for edition in ("fr", "en"):
        assert (out / edition / "media" / "pic.png").read_bytes() == data
        assert not (out / edition / "media" / "unused.png").exists()
        media = cast(
            list[dict[str, object]], _read(out / edition / "deck.json")["media"]
        )
        assert media == [
            {
                "filename": "pic.png",
                "sha256": sha256(data).hexdigest(),
                "size": len(data),
            }
        ]


def test_media_with_space_in_name(make_project: MakeProject, tmp_path: Path):
    cards = "cards:\n  - id: a\n    type: basic\n    front: '![x](media/a%20b.png)'\n    back: B\n"
    root = make_project({"cards/a.yaml": cards, "media/a b.png": b"1"})
    out = tmp_path / "out"
    assert build(root, out, "v") == []
    assert (out / "fr" / "media" / "a b.png").is_file()
    assert 'src=\\"a b.png\\"' in (out / "fr" / "deck.json").read_text(encoding="utf-8")


def test_media_name_collision(make_project: MakeProject, tmp_path: Path):
    cards = (
        "cards:\n  - id: a\n    type: basic\n"
        "    front: '![x](media/one/x.png)![y](media/two/x.png)'\n    back: B\n"
    )
    root = make_project(
        {"cards/a.yaml": cards, "media/one/x.png": b"1", "media/two/x.png": b"2"}
    )
    issues = build(root, tmp_path / "out", "v")
    assert [i.message for i in issues] == ["media name collision 'x.png'"] * 2
    assert not (tmp_path / "out").exists()


def test_deterministic_output(make_project: MakeProject, tmp_path: Path):
    root = make_project({"cards/a.yaml": CARDS})
    assert build(root, tmp_path / "o1", "same") == []
    assert build(root, tmp_path / "o2", "same") == []
    for edition in ("fr", "en"):
        assert (tmp_path / "o1" / edition / "deck.json").read_bytes() == (
            tmp_path / "o2" / edition / "deck.json"
        ).read_bytes()


def test_version_from_env_or_dev(
    make_project: MakeProject, monkeypatch: pytest.MonkeyPatch
):
    root = make_project({"cards/a.yaml": CARDS})
    monkeypatch.chdir(root)
    monkeypatch.delenv("DECKDOCK_VERSION", raising=False)
    assert main([]) == 0
    deck = cast(dict[str, object], _read(root / "dist" / "fr" / "deck.json")["deck"])
    assert deck["version"] == "dev"
    monkeypatch.setenv("DECKDOCK_VERSION", "2.0")
    assert main([]) == 0
    deck = cast(dict[str, object], _read(root / "dist" / "fr" / "deck.json")["deck"])
    assert deck["version"] == "2.0"


def test_cli_build_exit_codes(
    make_project: MakeProject,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    root = make_project({"cards/a.yaml": CARDS})
    monkeypatch.chdir(root)
    assert main(["--out", str(tmp_path / "o")]) == 0
    assert (tmp_path / "o" / "fr" / "deck.json").is_file()
    _ = (root / "cards" / "a.yaml").write_text("cards: nope\n", encoding="utf-8")
    _ = capsys.readouterr()
    assert main(["--out", str(tmp_path / "o2")]) == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "cards/a.yaml" in err
    assert not (tmp_path / "o2").exists()


def test_mcq_choices_html(make_project: MakeProject):
    cards = (
        "cards:\n  - id: q\n    type: mcq\n    question: Q?\n    choices:\n"
        "      - {text: A}\n      - {text: B, correct: true}\n      - {text: C}\n"
    )
    root = make_project({"cards/a.yaml": cards})
    project, issues = load_project(root)
    assert project is not None and issues == []
    deck, _ = compile_edition(project, "fr", "v")
    notes = cast(list[dict[str, dict[str, str]]], deck["notes"])
    choices = notes[0]["fields"]["Choices"]
    assert (
        choices
        == '<ol class="dd-choices"><li>A</li><li data-correct="1">B</li><li>C</li></ol>'
    )
    assert choices.count('data-correct="1"') == 1


def test_notetypes_only_used_in_first_use_order(make_project: MakeProject):
    cards = (
        "cards:\n  - id: c\n    type: cloze\n    text: '{{c1::x}}'\n"
        "  - id: b\n    type: basic\n    front: F\n    back: B\n"
        "  - id: c2\n    type: cloze\n    text: '{{c1::y}}'\n"
    )
    root = make_project({"cards/a.yaml": cards})
    project, _ = load_project(root)
    assert project is not None
    deck, _ = compile_edition(project, "en", "v")
    ids = [nt["id"] for nt in cast(list[dict[str, object]], deck["notetypes"])]
    assert ids == ["cloze", "basic"]


def test_name_description_str_or_dict(make_project: MakeProject):
    config = (
        "id: test-deck\nname: {fr: Nom, en: Name}\ndescription: Same\n"
        "editions: [fr, en]\nlicense: MIT\noptions: {new_per_day: 5}\n"
    )
    root = make_project({"deckdock.yaml": config, "cards/a.yaml": CARDS})
    project, _ = load_project(root)
    assert project is not None
    deck, _ = compile_edition(project, "en", "v")
    meta = deck["deck"]
    assert meta["name"] == "Name"
    assert meta.get("description") == "Same"
    assert meta.get("options") == {"new_per_day": 5}
    assert "homepage" not in meta
    assert list(meta) == [
        "id",
        "edition",
        "name",
        "language",
        "version",
        "description",
        "license",
        "generator",
        "options",
    ]


def test_refuses_to_clear_foreign_directory(make_project: MakeProject, tmp_path: Path):
    root = make_project({"cards/a.yaml": CARDS})
    foreign = tmp_path / "mine"
    foreign.mkdir()
    keep = foreign / "precious.txt"
    _ = keep.write_text("x")
    issues = build(root, foreign, "v")
    assert [i.message for i in issues] == [
        "refusing to overwrite non-deckdock directory"
    ]
    assert keep.read_text() == "x"


def test_rebuild_clears_previous_build(make_project: MakeProject, tmp_path: Path):
    root = make_project({"cards/a.yaml": CARDS})
    out = tmp_path / "out"
    assert build(root, out, "v") == []
    stale = out / "xx"
    stale.mkdir()
    _ = (stale / "deck.json").write_text("{}")
    assert build(root, out, "v") == []
    assert not stale.exists()


def _front_card(front: str) -> str:
    return f'cards:\n  - id: a\n    type: basic\n    front: "{front}"\n    back: B\n'


def test_reference_style_traversal_not_copied(
    make_project: MakeProject, tmp_path: Path
):
    root = make_project(
        {
            "cards/a.yaml": _front_card("![x][r]\\n\\n[r]: media/../secret.txt"),
            "secret.txt": "s",
        }
    )
    out = tmp_path / "out"
    issues = build(root, out, "v")
    assert [i.message for i in issues] == [
        "media must live in media/ (got 'media/../secret.txt')"
    ]
    assert not out.exists()


@pytest.mark.parametrize(
    ("front", "message"),
    [
        (
            "![x][r]\\n\\n[r]: media/../secret.txt",
            "media must live in media/ (got 'media/../secret.txt')",
        ),
        (
            "![x](media/../secret.txt)",
            "media must live in media/ (got 'media/../secret.txt')",
        ),
        ("![x][r]\\n\\n[r]: media/nope.png", "missing media file 'media/nope.png'"),
        ("![x](media/link.png)", "media file 'media/link.png' resolves outside media/"),
    ],
)
def test_builder_guards_media_even_without_validation(
    make_project: MakeProject,
    tmp_path_factory: pytest.TempPathFactory,
    monkeypatch: pytest.MonkeyPatch,
    front: str,
    message: str,
):
    outside = tmp_path_factory.mktemp("outside") / "secret.png"
    _ = outside.write_bytes(b"secret")
    root = make_project({"cards/a.yaml": _front_card(front), "secret.txt": "s"})
    (root / "media").mkdir()
    (root / "media" / "link.png").symlink_to(outside)

    def no_validation(_project: Project) -> list[Issue]:
        return []

    monkeypatch.setattr("compiler.builder.validate_project", no_validation)
    out = tmp_path_factory.mktemp("build") / "out"
    issues = build(root, out, "v")
    assert {i.message for i in issues} == {message}
    assert not out.exists()


@pytest.mark.parametrize("absolute", [False, True])
def test_edition_code_cannot_escape_out(tmp_path: Path, absolute: bool):
    escaped = tmp_path / "escaped"
    code = str(escaped) if absolute else "../../escaped"
    root = tmp_path / "a" / "proj"
    (root / "cards").mkdir(parents=True)
    _ = (root / "deckdock.yaml").write_text(
        f"id: x\nname: X\neditions: [{json.dumps(code)}]\n", encoding="utf-8"
    )
    _ = (root / "cards" / "a.yaml").write_text(
        "cards:\n  - id: a\n    type: basic\n    front: F\n    back: B\n",
        encoding="utf-8",
    )
    issues = build(root, root / "dist", "v")
    assert len(issues) == 1
    assert "invalid edition code" in issues[0].message
    assert not escaped.exists()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a"]


def test_symlinked_dist_is_an_issue(
    make_project: MakeProject, tmp_path_factory: pytest.TempPathFactory
):
    root = make_project({"cards/a.yaml": CARDS})
    target = tmp_path_factory.mktemp("real-dist")
    (root / "dist").symlink_to(target, target_is_directory=True)
    issues = build(root, root / "dist", "v")
    assert [str(i) for i in issues] == [
        f"{root / 'dist'}: output directory is a symbolic link; refusing to clear it"
    ]
    assert (root / "dist").is_symlink()


def test_copy_failure_is_an_issue(make_project: MakeProject, tmp_path: Path):
    cards = "cards:\n  - id: a\n    type: basic\n    front: '![x](media/p.png)'\n    back: B\n"
    root = make_project({"cards/a.yaml": cards, "media/p.png": b"x"})
    source = root / "media" / "p.png"
    source.chmod(0)
    if os.access(source, os.R_OK):
        source.chmod(0o644)
        pytest.skip("permissions are not enforced")
    try:
        issues = build(root, tmp_path / "out", "v")
    finally:
        source.chmod(0o644)
    assert len(issues) == 1
    assert issues[0].path == str(tmp_path / "out")
    assert issues[0].message.startswith("cannot write output:")
