"""Write `<dist>/index.json` (deckdock-index/1) from the `<dist>/*/deck.json` files."""

import json
import sys
from pathlib import Path
from typing import cast

INDEX_FORMAT = "deckdock-index/1"


def make_index(dist: Path) -> dict[str, object]:
    """List every edition found under `dist`, sorted by edition code."""
    editions: list[dict[str, object]] = []
    for path in sorted(dist.glob("*/deck.json")):
        data = cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
        deck = cast(dict[str, object], data["deck"])
        editions.append(
            {
                "edition": deck["edition"],
                "name": deck["name"],
                "language": deck["language"],
                "version": deck["version"],
            }
        )
    editions.sort(key=lambda entry: str(entry["edition"]))
    return {"format": INDEX_FORMAT, "editions": editions}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        _ = sys.stderr.write("usage: make_index.py DIST\n")
        return 2
    dist = Path(args[0])
    text = json.dumps(make_index(dist), ensure_ascii=False, indent=2) + "\n"
    _ = (dist / "index.json").write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
