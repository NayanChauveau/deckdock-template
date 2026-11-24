# My deck

An Anki deck written as YAML, compiled into JSON by the example compiler in this repo, in the
[DeckDock](https://github.com/NayanChauveau/deckdock) format.
This repo ships with three example cards (basic, cloze, multiple choice) in French and English.

## Get started

1. **Use this template.** Click "Use this template" on GitHub to create your own repo.
2. **Edit `deckdock.yaml`.** Set the deck `id` (lowercase letters, digits and dashes), the
   `name` and `description`, and the `editions` you publish (one per language code, such as
   `fr` or `en`). Choose the `id`, edition codes and card ids carefully: once the deck is
   published they are permanent, because changing any of them resets users' review history.
3. **Add cards.** Create files in `cards/` (see [AGENTS.md](AGENTS.md) for the four card
   types), put images in `media/`, and delete the `hello-*` example cards.
4. **Compile locally (optional).** Needs [uv](https://docs.astral.sh/uv/):

   ```bash
   uv run compile                  # validate, then write dist/<edition>/deck.json
   uv run compile --validate-only  # validate the sources, write nothing
   ```

5. **Push.** CI runs the tests, compiles the deck and checks the result.

## Your own compiler

This repo contains its own compiler (the `compiler/` folder): modify it freely. It is an
example of how to turn YAML into the `deckdock/1` JSON format, and nothing more. The only
requirement is that the `dist/` it produces passes `deckdock check`. See
"Changing the compiler" in [AGENTS.md](AGENTS.md), and
[docs/source-format.md](docs/source-format.md) for the YAML format it reads.

## Getting the JSON

Every push and pull request runs the compiler in GitHub Actions. Open the run and download the
`deck` artifact: it contains `<edition>/deck.json` and `<edition>/media/` for each edition.

After each push to `main`, the `dist` branch contains the compiled deck: subscribe in DeckDock
with the repository URL.

## Writing cards

- [AGENTS.md](AGENTS.md): file layout, card formats, rules and commands. Also the brief for AI coding agents.
- [CONTENT_GUIDELINES.md](CONTENT_GUIDELINES.md): how to write good cards.

## Format

The compiled format is described in the
[deckdock/1 specification](https://github.com/NayanChauveau/deckdock/blob/main/spec/deckdock-1.md).

## License

Tooling: MIT ([LICENSE](LICENSE)). Example content: CC0-1.0 ([LICENSE-CONTENT](LICENSE-CONTENT)).
