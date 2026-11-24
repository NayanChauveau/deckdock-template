# Content guidelines

How to write good cards for this deck. Replace the intro below with the scope of your own deck.

## Original wording

- Write questions and explanations in your own words.
- Facts are free to use. The way they are expressed is not: do not copy sentences, tables
  or exam items from copyrighted material.
- Do not paste page numbers or long quotations into cards.

## Card design

- **Atomic.** One card tests one fact or one idea. Split a card that asks "which, and why".
- **Unambiguous.** The question has one defensible answer. Include the context needed to
  answer it (country, period, version) in the question itself.
- **Short.** Keep prompts and answers brief. A long answer is usually several cards.
- **Active recall.** Ask for the answer rather than showing it. Avoid yes/no questions.
- **No clues by form.** In an MCQ, the right choice must not stand out by length or style.
- **Credible distractors.** Wrong choices belong to the same category as the right one and
  would tempt someone who half-remembers. Joke options test nothing.
- **Explain.** In `explanation` or `extra`, add something that helps memory (a reason, an
  example, an exception). Do not just repeat the answer. Never write "option B": choice
  order may change.
- **Pick the right type.** `basic` for a prompt and an answer, `reversed` when both
  directions are worth knowing, `cloze` for a fact inside a sentence or an ordered list,
  `mcq` when telling similar options apart is the skill.

## Sources

- Check any fact you are not sure of (dates, figures, rankings, names, legal rules) in an
  authoritative source.
- Cite the source in `extra` or `explanation` (for example `Source: <name>, <year>`), so a
  reviewer can verify it.

## Formatting

- Markdown is allowed (`**bold**`, lists, short paragraphs). A single newline is only source
  wrapping; use a blank line for a real new paragraph.
- Quote YAML strings that contain `:`, `#`, a leading `{` or `*`, and MCQ `text` containing a comma.
- Put images in `media/`, reference them as `media/<name>`, and give them alt text.

## Ids, tags and status

- `id` is permanent (`topic-subtopic-001`). Never rename or reuse it after release.
- Use `deck` for sub-decks (`Topic::Sub`) and `tags` for cross-cutting labels.
- `status: draft` while a card is unfinished or unchecked; it is left out of the build.
  Remove it (or set `reviewed`) when the card is ready.

## Translation

- Translate in the same file, on the same `id`, in the other edition block.
- Translate the meaning, not the word order. Read the result as a native speaker would.
- Keep the same number of choices and the same correct choice in every edition.
- If you change a fact in one edition, update the other editions in the same pull request.
- A card missing from an edition is simply omitted from that edition.

## Tone

Neutral, precise, calm. No marketing, no trick questions that hinge on a single word.
