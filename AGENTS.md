# Agent instructions

Brief for coding agents (Claude, Codex, Cursor, etc.) and humans adding cards to this deck.
Read [CONTENT_GUIDELINES.md](CONTENT_GUIDELINES.md) before writing cards.

## What this repo is

An Anki deck written as YAML. The YAML in `cards/` is the source of truth;
[DeckDock](https://github.com/NayanChauveau/deckdock) compiles it into one JSON file per
edition (`dist/<edition>/deck.json` plus `dist/<edition>/media/`), in the `deckdock/1` format.

## Layout

| Path | Role |
| --- | --- |
| `deckdock.yaml` | Deck id, name, description, editions, license |
| `cards/*.yaml` | Cards. One file per topic, many cards per file |
| `media/` | Images and audio used by cards |
| `dist/` | Build output. Generated, git-ignored |

## Hard rules

- Card `id` values are permanent. Never rename or reuse a released id: Anki progress is tied to it.
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

Give at least 2 choices, exactly one with `correct: true` (`validate` enforces both). Quote `text` if it contains a comma or a colon.
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

Run from the repo root. `uvx` fetches DeckDock on demand, nothing to install.

```bash
# Check the YAML sources (run this after every change)
uvx --from git+https://github.com/NayanChauveau/deckdock@v1#subdirectory=cli deckdock validate

# Compile into dist/<edition>/deck.json
uvx --from git+https://github.com/NayanChauveau/deckdock@v1#subdirectory=cli deckdock build
```

Errors are reported as `path:line: message`. Fix all of them before committing. CI runs
`build` on every pull request and on `main`.
