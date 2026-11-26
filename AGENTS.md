# Agent instructions

Brief for coding agents (Claude, Codex, Cursor, etc.) and humans adding cards to this deck.
Read [CONTENT_GUIDELINES.md](CONTENT_GUIDELINES.md) before writing cards.

## What this repo is

An Anki deck written as YAML. The YAML in `cards/` is the source of truth. The compiler in
`compiler/` turns it into one JSON file per edition (`dist/<edition>/deck.json` plus
`dist/<edition>/media/`), in the [`deckdock/1`](https://github.com/NayanChauveau/deckdock/blob/main/spec/deckdock-1.md) format.

## Layout

| Path | Role |
| --- | --- |
| `deckdock.yaml` | Deck id, name, icon, description, editions, license, homepage |
| `cards/*.yaml` | Cards. One file per topic, many cards per file |
| `media/` | Images and audio used by cards |
| `dist/` | Compiler output. Generated, git-ignored. CI publishes it, plus `index.json` (from `scripts/make_index.py`), to the `dist` branch on each push to `main` |
| `compiler/` | The example compiler (see "Changing the compiler") |
| `tests/` | Tests of the compiler and of the docs examples |
| `schema/source.schema.json` | JSON Schema of the YAML, for editor support |
| `docs/source-format.md` | The YAML format read by the compiler |

## Hard rules

- The deck `id` and the `editions` codes in `deckdock.yaml`, and every card `id`, are permanent once published.
  Anki note GUIDs are derived from them: changing any of them resets every user's review history. Never rename or reuse them.
- Never change the structure (fields, templates, kind) of a published notetype: see "Changing a published notetype".
- Ids are lowercase letters, digits and single dashes (`topic-subtopic-001`), unique across the whole project.
- Append cards to the existing topic file. Do not create one file per card.
- Every media file lives in `media/` and is referenced as `media/<name>`. No other path is accepted.
- New cards start as `status: draft` (excluded from the build). Switch to `reviewed` (the default) once checked.
- Check doubtful facts (dates, figures, names, rules) against an authoritative source. Never rely on memory.
- Write original wording. Do not copy text from books, courses or exams you do not own.

## Card types

A card's content is either written directly (same in every edition) or in one block per
edition (`fr:`, `en:`, ...). A card present in only one edition is omitted from the others.
Do not mix both styles in one card. Edition codes must match `editions` in `deckdock.yaml`.

Common optional keys: `deck` (sub-deck path such as `Topic::Sub`, default is the root),
`tags` (list), `status` (`draft` or `reviewed`).

### basic

```yaml
- id: capitals-001
  type: basic
  tags: [europe]
  en:
    front: What is the capital of Australia?
    back: Canberra
  fr:
    front: Quelle est la capitale de l'Australie ?
    back: Canberra
```

### reversed

Same fields as `basic`, but Anki also generates the back-to-front card.

```yaml
- id: capitals-002
  type: reversed
  front: Canberra
  back: Capital of Australia
```

### cloze

Use `{{c1::...}}` for each deletion. Numbers (`c1`, `c2`, ...) group deletions into cards.
`extra` is optional and shown on the back.

```yaml
- id: biology-001
  type: cloze
  en:
    text: "{{c1::Mitochondria}} produce most of the cell's {{c2::ATP}}."
    extra: "Source: course notes, week 3."
```

### mcq

Give at least 2 choices, exactly one with `correct: true` (the compiler enforces both). Quote `text` if it contains a comma or a colon.
`explanation` is optional and shown on the back.

```yaml
- id: geography-001
  type: mcq
  en:
    question: Which river flows through Paris?
    choices:
      - {text: Seine, correct: true}
      - {text: Loire}
      - {text: Rhône}
    explanation: The Loire and the Rhône are other major French rivers.
```

### Images

Put the file in `media/` and use Markdown (`![alt text](media/map.png)`). Text fields accept
Markdown and inline HTML. Write alt text that describes the image.

## Commands

Run from the repo root. [uv](https://docs.astral.sh/uv/) installs everything on first use.

```bash
# Check the YAML sources (run this after every change)
uv run compile --validate-only

# Validate, then compile into dist/<edition>/deck.json
uv run compile

# Run the tests
uv run pytest
```

Errors are reported as `path:line: message`. Fix all of them before committing. CI runs the
tests, then compiles the deck and checks it with `deckdock check`, on every pull request and
on `main`. To publish to the DeckDock hub, the repository needs the secret `DECKDOCK_TOKEN` and the variable `DECKDOCK_HUB_URL`; CI then uploads each edition on push to `main`. The version is the commit's time (UTC) and short SHA, so re-running the workflow of the same commit uploads the same version (the hub answers `already_published`). Only the publish step receives the token.

## Changing the compiler

The compiler is an example: change it as you need. The only obligation is that the `dist/` it
writes passes `deckdock check` (CI runs it). Where things live:

| Path | Role |
| --- | --- |
| `compiler/cli.py` | `uv run compile`: arguments, exit code |
| `compiler/source/models.py` | Pydantic models of `deckdock.yaml` and of cards; also generates `schema/source.schema.json` |
| `compiler/source/load.py` | Reads the YAML files, keeps line numbers for errors |
| `compiler/source/validate.py` | Rules that models cannot express (ids, media, editions) |
| `compiler/render/markdown.py` | Markdown to HTML for card text |
| `compiler/media.py` | Media path rules (only `media/<name>`, no symlinks, size limits) |
| `compiler/notetypes.py`, `compiler/notetypes/` | Notetype definitions, and their HTML/CSS/JS templates |
| `compiler/builder.py` | Turns a validated project into `deck.json` files and copies media |

To add a card type:

1. Add a notetype: its templates in `compiler/notetypes/` and its entry in `compiler/notetypes.py`.
2. Add a content model for it in `compiler/source/models.py`, and handle it in
   `compiler/builder.py` and `compiler/source/validate.py`.
3. Regenerate the schema and document the type in this file:
   `uv run python -c "import json; from compiler.source.models import source_json_schema as s; print(json.dumps(s(), indent=2, ensure_ascii=False))" > schema/source.schema.json`
   (check the diff: it must match the existing formatting).
4. Add tests in `tests/` and run `uv run pytest`, then `uv run compile`.

The library `deckdock` (a dependency) provides the format types, `check_dist`, `guid_for` and
`card_guid`; use them instead of re-implementing them.

### Changing a published notetype

Once the deck is published, subscribers have its notetypes in their Anki collection. Before
changing a notetype in `compiler/notetypes.py` or `compiler/notetypes/`, check which kind of
change it is:

| Change | Effect on subscribers |
| --- | --- |
| Card text (fields' values), tags, adding or retiring cards, template text (HTML layout), CSS | Safe: applied normally, review history kept |
| Adding a field **at the end** of a notetype | Requires a full AnkiWeb sync: subscribers must confirm and sync their other devices first, or unsynced reviews from those devices can be lost. Avoid unless necessary, and say so in the release notes |
| Removing, renaming or reordering fields; adding or removing a template (a card side); switching between basic and cloze | **Blocked**: subscribers' updates are refused and they stay on the old version. Never do this to a published notetype |

To change the structure of a published card type, create a new notetype (a new `id`) and use it
for new cards instead of editing the old one.
