from collections.abc import Callable
from pathlib import Path

import pytest

from compiler.cli import main
from compiler.source.load import load_project
from compiler.source.validate import validate_project

MakeProject = Callable[[dict[str, str | bytes]], Path]


def messages(root: Path) -> list[str]:
    project, load_issues = load_project(root)
    assert project is not None, [str(i) for i in load_issues]
    return [str(i) for i in validate_project(project)]


def basic(card_id: str = "a-1", extra: str = "") -> str:
    return f"  - id: {card_id}\n    type: basic\n    front: x\n    back: y\n{extra}"


def test_valid_project_has_no_issues(make_project: MakeProject):
    assert messages(make_project({"cards/a.yaml": "cards:\n" + basic()})) == []


@pytest.mark.parametrize("bad", ["Hello", "a_b", "-a", "a--b", "hello-001\\n"])
def test_invalid_card_id(make_project: MakeProject, bad: str):
    root = make_project(
        {
            "cards/a.yaml": f'cards:\n  - id: "{bad}"\n    type: basic\n    front: x\n    back: y\n'
        }
    )
    assert any("invalid card id" in m for m in messages(root))


def test_trailing_newline_card_id_rejected(make_project: MakeProject):
    root = make_project(
        {
            "cards/a.yaml": 'cards:\n  - id: "hello-001\\n"\n    type: basic\n    front: x\n    back: y\n'
        }
    )
    assert messages(root) == ["cards/a.yaml:2: invalid card id 'hello-001\\n'"]


def test_invalid_project_id(make_project: MakeProject):
    root = make_project(
        {
            "deckdock.yaml": "id: Bad_Id\nname: T\neditions: [fr]\n",
            "cards/a.yaml": "cards:\n" + basic(),
        }
    )
    assert messages(root) == ["deckdock.yaml: invalid project id 'Bad_Id'"]


def test_duplicate_id_across_files_names_both(make_project: MakeProject):
    root = make_project(
        {
            "cards/a.yaml": "cards:\n\n\n" + basic("dup"),
            "cards/b.yaml": "cards:\n" + basic("dup"),
        }
    )
    assert messages(root) == [
        "cards/b.yaml:2: duplicate card id 'dup' (also at cards/a.yaml:4)"
    ]


def test_duplicate_id_in_same_file(make_project: MakeProject):
    root = make_project({"cards/a.yaml": "cards:\n" + basic("dup") + basic("dup")})
    assert messages(root) == [
        "cards/a.yaml:6: duplicate card id 'dup' (also at cards/a.yaml:2)"
    ]


def test_unknown_edition(make_project: MakeProject):
    text = "cards:\n  - id: a\n    type: basic\n    de: { front: x, back: y }\n"
    assert messages(make_project({"cards/a.yaml": text})) == [
        "cards/a.yaml:2: unknown edition 'de'"
    ]


def test_no_content_for_any_edition(make_project: MakeProject):
    root = make_project({"cards/a.yaml": "cards:\n  - id: a\n    type: basic\n"})
    assert messages(root) == ["cards/a.yaml:2: no content for any edition"]


def test_cloze_without_deletion(make_project: MakeProject):
    text = (
        "cards:\n  - id: a\n    type: cloze\n    fr: { text: 'no deletion {{here}}' }\n"
    )
    assert messages(make_project({"cards/a.yaml": text})) == [
        "cards/a.yaml:2: cloze text has no deletion (edition 'fr')"
    ]


def test_cloze_with_deletion_ok(make_project: MakeProject):
    text = "cards:\n  - id: a\n    type: cloze\n    text: 'The {{c1::sky}} is {{c2::blue}}'\n"
    assert messages(make_project({"cards/a.yaml": text})) == []


@pytest.mark.parametrize(
    "choices",
    [
        "[{text: a, correct: true}]",
        "[{text: a}, {text: b}]",
        "[{text: a, correct: true}, {text: b, correct: true}]",
    ],
)
def test_mcq_needs_two_choices_and_one_correct(make_project: MakeProject, choices: str):
    text = (
        f"cards:\n  - id: a\n    type: mcq\n    question: q\n    choices: {choices}\n"
    )
    assert any(
        "exactly one correct choice" in m
        for m in messages(make_project({"cards/a.yaml": text}))
    )


def test_mcq_valid(make_project: MakeProject):
    text = "cards:\n  - id: a\n    type: mcq\n    question: q\n    choices: [{text: a}, {text: b, correct: true}]\n"
    assert messages(make_project({"cards/a.yaml": text})) == []


def test_media_outside_media_dir(make_project: MakeProject):
    text = "cards:\n  - id: a\n    type: cloze\n    text: '{{c1::x}} ![](img/a.png)'\n"
    root = make_project({"cards/a.yaml": text, "img/a.png": b"x"})
    assert any("media must live in media/" in m for m in messages(root))


def test_media_traversal_rejected(make_project: MakeProject):
    text = "cards:\n  - id: a\n    type: basic\n    front: '![](media/../secret.png)'\n    back: y\n"
    root = make_project({"cards/a.yaml": text, "secret.png": b"x"})
    assert any("media must live in media/" in m for m in messages(root))


def test_missing_media_file(make_project: MakeProject):
    text = "cards:\n  - id: a\n    type: basic\n    front: '![](media/x.png)'\n    back: y\n"
    assert messages(make_project({"cards/a.yaml": text})) == [
        "cards/a.yaml:2: missing media file 'media/x.png'"
    ]


def test_html_src_and_percent_encoded_media(make_project: MakeProject):
    text = (
        "cards:\n  - id: a\n    type: basic\n"
        "    front: '![](media/my%20pic.png) <img src=\"media/b.png\"> <img src=''media/c.png''>'\n"
        "    back: '![alt](<media/with space.png> \"title\")'\n"
    )
    files: dict[str, str | bytes] = {
        "cards/a.yaml": text,
        "media/my pic.png": b"x",
        "media/b.png": b"x",
    }
    root = make_project(files)
    assert messages(root) == [
        "cards/a.yaml:2: missing media file 'media/c.png'",
        "cards/a.yaml:2: missing media file 'media/with space.png'",
    ]


def test_remote_and_data_media_ignored(make_project: MakeProject):
    text = (
        "cards:\n  - id: a\n    type: basic\n"
        "    front: '![](https://example.com/a.png) <img src=\"data:image/png;base64,AAAA\">'\n"
        "    back: y\n"
    )
    assert messages(make_project({"cards/a.yaml": text})) == []


def test_empty_deck_segment(make_project: MakeProject):
    root = make_project(
        {"cards/a.yaml": "cards:\n" + basic(extra="    deck: 'A::::B'\n")}
    )
    assert any("deck path" in m for m in messages(root))
    root_ok = make_project(
        {"cards/b.yaml": "cards:\n" + basic("b-1", "    deck: 'A::B'\n")}
    )
    assert not any("deck path" in m for m in messages(root_ok) if "b.yaml" in m)


def test_name_dict_missing_edition(make_project: MakeProject):
    root = make_project(
        {
            "deckdock.yaml": "id: t\nname: {fr: T}\ndescription: {fr: D}\neditions: [fr, en]\n",
            "cards/a.yaml": "cards:\n" + basic(),
        }
    )
    assert messages(root) == [
        "deckdock.yaml: missing name for edition 'en'",
        "deckdock.yaml: missing description for edition 'en'",
    ]


def test_cli_validate_exit_codes(
    make_project: MakeProject,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    good = make_project({"cards/a.yaml": "cards:\n" + basic()})
    monkeypatch.chdir(good)
    assert main(["--validate-only"]) == 0
    assert capsys.readouterr().err == ""
    _ = (good / "cards" / "a.yaml").write_text(
        "cards:\n" + basic("Bad Id"), encoding="utf-8"
    )
    assert main(["--validate-only"]) == 1
    assert capsys.readouterr().err == "cards/a.yaml:2: invalid card id 'Bad Id'\n"


def test_cli_validate_reports_load_errors(
    make_project: MakeProject,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
):
    monkeypatch.chdir(make_project({"cards/a.yaml": "cards: [\n"}))
    assert main(["--validate-only"]) == 1
    assert "cards/a.yaml:2: invalid YAML" in capsys.readouterr().err


def test_cli_validate_only_writes_nothing(
    make_project: MakeProject, monkeypatch: pytest.MonkeyPatch
):
    root = make_project({"cards/a.yaml": "cards:\n" + basic()})
    monkeypatch.chdir(root)
    assert main(["--validate-only"]) == 0
    assert not (root / "dist").exists()


def _front(front: str) -> str:
    return f'cards:\n  - id: a\n    type: basic\n    front: "{front}"\n    back: y\n'


def test_reference_style_image_traversal_rejected(make_project: MakeProject):
    root = make_project(
        {
            "cards/a.yaml": _front("![x][r]\\n\\n[r]: media/../secret.txt"),
            "secret.txt": "s",
        }
    )
    assert messages(root) == [
        "cards/a.yaml:2: media must live in media/ (got 'media/../secret.txt')"
    ]


def test_reference_style_missing_target(make_project: MakeProject):
    root = make_project({"cards/a.yaml": _front("![x][r]\\n\\n[r]: media/nope.png")})
    assert messages(root) == ["cards/a.yaml:2: missing media file 'media/nope.png'"]


def test_html_src_outside_media_rejected(make_project: MakeProject):
    root = make_project(
        {"cards/a.yaml": _front("<img src='img/a.png'>"), "img/a.png": b"x"}
    )
    assert messages(root) == [
        "cards/a.yaml:2: media must live in media/ (got 'img/a.png')"
    ]


def test_symlink_escaping_media_rejected(
    make_project: MakeProject, tmp_path_factory: pytest.TempPathFactory
):
    outside = tmp_path_factory.mktemp("outside") / "secret.png"
    _ = outside.write_bytes(b"secret")
    root = make_project(
        {"cards/a.yaml": _front("![x](media/link.png)"), "inside.png": b"x"}
    )
    (root / "media").mkdir()
    (root / "media" / "link.png").symlink_to(outside)
    assert messages(root) == [
        "cards/a.yaml:2: media file 'media/link.png' resolves outside media/"
    ]
    (root / "media" / "link.png").unlink()
    (root / "media" / "link.png").symlink_to(root / "inside.png")
    assert messages(root) == [
        "cards/a.yaml:2: media file 'media/link.png' resolves outside media/"
    ]


def test_symlinked_media_dir_outside_project_rejected(
    make_project: MakeProject, tmp_path_factory: pytest.TempPathFactory
):
    outside = tmp_path_factory.mktemp("elsewhere")
    _ = (outside / "x.png").write_bytes(b"x")
    root = make_project({"cards/a.yaml": _front("![x](media/x.png)")})
    (root / "media").symlink_to(outside)
    assert messages(root) == [
        "cards/a.yaml:2: media file 'media/x.png' resolves outside media/"
    ]


def test_symlink_inside_media_accepted(make_project: MakeProject):
    root = make_project(
        {"cards/a.yaml": _front("![x](media/link.png)"), "media/real.png": b"x"}
    )
    (root / "media" / "link.png").symlink_to("real.png")
    assert messages(root) == []


def test_media_directory_is_not_a_file(make_project: MakeProject):
    root = make_project(
        {"cards/a.yaml": _front("![x](media/dir)"), "media/dir/x.png": b"x"}
    )
    assert messages(root) == ["cards/a.yaml:2: missing media file 'media/dir'"]


@pytest.mark.parametrize("icon", ["📚📚", "a", "'📚 '"])
def test_icon_must_be_a_single_emoji(make_project: MakeProject, icon: str):
    root = make_project(
        {
            "deckdock.yaml": f"id: test-deck\nname: T\nicon: {icon}\neditions: [fr]\n",
            "cards/a.yaml": "cards:\n" + basic(),
        }
    )
    assert messages(root) == ["deckdock.yaml: icon must be a single emoji"]
