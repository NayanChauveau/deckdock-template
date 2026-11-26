# Source format of the example compiler

This is the format of the YAML files read by the example compiler of this repo (`compiler/`),
which `uv run compile` turns into the
[`deckdock/1`](https://github.com/NayanChauveau/deckdock/blob/main/spec/deckdock-1.md) JSON format.
It is not part of the deckdock format: you can change it together with the compiler. Editor
support: [`schema/source.schema.json`](../schema/source.schema.json) (generated from the
compiler's models). This page is a high-level description; the compiler is the reference.

## Layout

```
deckdock.yaml      # project file
cards/**/*.yaml    # cards (.yaml or .yml), any number of files and sub-folders
media/             # images and audio referenced by cards
dist/              # compiler output (generated)
```

## `deckdock.yaml`

| Key | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Deck id: lowercase letters, digits and single dashes (`^[a-z0-9]+(?:-[a-z0-9]+)*$`). Becomes `deck.id`. **Permanent.** |
| `name` | yes | Deck name: a string, or a mapping edition code -> string covering every edition. |
| `editions` | yes | Non-empty list of unique edition codes, same pattern as `id`. **Permanent.** |
| `description` | no | A string, or a mapping edition code -> string covering every edition. |
| `icon` | no | One emoji shown next to the deck on the hub (a flag, a combined emoji or a skin tone counts as one). |
| `license` | no | String copied to the compiled deck. |
| `homepage` | no | String copied to the compiled deck. If absent, a build on GitHub Actions uses the repository's address (`GITHUB_SERVER_URL`/`GITHUB_REPOSITORY`); a local build leaves it out. |
| `options` | no | `new_per_day`, `reviews_per_day` (integers >= 0). |

In this simple format an edition code is a **language code** (`fr`, `en`, `pt-br`...): the
edition `fr` compiles to `dist/fr/deck.json` with `deck.language` set to `["fr"]`.

## Cards

Each `cards/*.yaml` file holds a mapping with one key, `cards`, a list of cards:

| Key | Required | Meaning |
| --- | --- | --- |
| `id` | yes | Card id, same pattern as the deck id, unique across the whole project. **Permanent.** |
| `type` | yes | `basic`, `reversed`, `cloze` or `mcq`. |
| `deck` | no | Sub-deck path such as `Topic::Sub` (default: the root deck). |
| `tags` | no | List of tags. |
| `status` | no | `reviewed` (default) or `draft`; drafts are left out of the build. |

Content keys depend on the type: `front`, `back` (`basic`, `reversed`); `text`, `extra`
(`cloze`); `question`, `choices` (list of `{text, correct}`), `explanation` (`mcq`). Content is
written either directly on the card (the same in every edition) or in one block per edition
(`fr: {front: ..., back: ...}`); a card without a block for an edition is omitted from it.

Text is Markdown with inline HTML, rendered to HTML at build time. Media files live in
`media/` and are referenced as `media/<name>` (Markdown images or `src` attributes); the
compiled deck refers to them by bare filename.

## GUIDs and permanence

Each compiled note gets the Anki GUID

```
guid = guid_for("deckdock", deck_id, card_id, edition)
```

where `guid_for` is compatible with `genanki.guid_for`: the values are joined with `"__"`, hashed
with SHA-256, the first 8 bytes of the digest are read as a big-endian integer, and that integer
is written in base 91 (alphabet: ASCII letters, digits, then `` !#$%&()*+,-./:;<=>?@[]^_`{|}~ ``).

The GUID is how Anki recognizes a note across updates. The deck `id`, the edition codes and the
card ids are therefore **permanent**: changing any of them changes the GUIDs, so every user who
updates gets new notes and loses the review history of the old ones. Never rename or reuse them
once a deck is published.
