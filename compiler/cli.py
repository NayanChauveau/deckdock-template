"""Command-line entry point: validate the sources in the current folder, then write dist/."""

import argparse
import os
from pathlib import Path
from typing import cast

from deckdock.issues import print_issues

from compiler.builder import build
from compiler.source.load import load_project
from compiler.source.validate import validate_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compile",
        description="Compile the deck in the current folder into dist/<edition>/.",
    )
    _ = parser.add_argument(
        "--validate-only",
        action="store_true",
        help="validate the YAML sources and write nothing",
    )
    _ = parser.add_argument(
        "--out", default=None, help="output directory (default: dist)"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(".")
    if cast(bool, args.validate_only):
        project, issues = load_project(root)
        if project is not None:
            issues = validate_project(project)
        return print_issues(issues)
    out_arg = cast(str | None, args.out)
    out = Path(out_arg) if out_arg is not None else root / "dist"
    version = os.environ.get("DECKDOCK_VERSION", "dev")
    return print_issues(build(root, out, version))
