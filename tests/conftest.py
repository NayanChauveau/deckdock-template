from collections.abc import Callable
from pathlib import Path

import pytest

DEFAULT_CONFIG = "id: test-deck\nname: Test\neditions: [fr, en]\n"


@pytest.fixture
def make_project(tmp_path: Path) -> Callable[[dict[str, str | bytes]], Path]:
    """Write `files` (relative path -> content) under tmp_path and return the root.

    A minimal valid deckdock.yaml is provided unless the key is present.
    """

    def _make(files: dict[str, str | bytes]) -> Path:
        files = dict(files)
        _ = files.setdefault("deckdock.yaml", DEFAULT_CONFIG)
        for rel, content in files.items():
            target = tmp_path / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                _ = target.write_bytes(content)
            else:
                _ = target.write_text(content, encoding="utf-8")
        return tmp_path

    return _make
