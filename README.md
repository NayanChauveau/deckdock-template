# My deck

An Anki deck written as YAML, built into JSON by [DeckDock](https://github.com/NayanChauveau/deckdock).
This repo ships with three example cards (basic, cloze, multiple choice) in French and English.

## Get started

1. **Use this template.** Click "Use this template" on GitHub to create your own repo.
2. **Edit `deckdock.yaml`.** Set the deck `id` (lowercase letters, digits and dashes), the
   `name` and `description`, and the `editions` you publish (one per language).
3. **Add cards and push.** Create files in `cards/` (see [AGENTS.md](AGENTS.md) for the four
   card types), put images in `media/`, then commit and push. Delete the `hello-*` example cards.

To check your work locally (needs [uv](https://docs.astral.sh/uv/)):

```bash
uvx --from git+https://github.com/NayanChauveau/deckdock@v1#subdirectory=cli deckdock validate
uvx --from git+https://github.com/NayanChauveau/deckdock@v1#subdirectory=cli deckdock build
```

## Getting the JSON

Every push and pull request runs the build in GitHub Actions. Open the run and download the
`deck` artifact: it contains `<edition>/deck.json` and `<edition>/media/` for each edition.

## Writing cards

- [AGENTS.md](AGENTS.md): file layout, card formats, rules and commands. Also the brief for AI coding agents.
- [CONTENT_GUIDELINES.md](CONTENT_GUIDELINES.md): how to write good cards.

## Format

The compiled format is described in the
[deckdock/1 specification](https://github.com/NayanChauveau/deckdock/blob/v1/spec/deckdock-1.md).

## License

Tooling: MIT ([LICENSE](LICENSE)). Example content: CC0-1.0 ([LICENSE-CONTENT](LICENSE-CONTENT)).
