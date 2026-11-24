"""Markdown to HTML rendering with media path rewriting."""

import html as html_lib
import re
from collections.abc import Sequence
from typing import cast, override
from urllib.parse import unquote

from markdown_it import MarkdownIt
from markdown_it.renderer import RendererHTML
from markdown_it.token import Token
from markdown_it.utils import EnvType, OptionsDict

from compiler.media import MEDIA_DIR, is_local

MEDIA_PREFIX = MEDIA_DIR + "/"
_RAW_SRC = re.compile(r"""(\bsrc\s*=\s*)(["'])([^"']*)\2""", re.IGNORECASE)


def _basename(path: str) -> str:
    return path.removeprefix(MEDIA_PREFIX).rsplit("/", 1)[-1]


class _MediaRenderer(RendererHTML):
    """HTML renderer that collects local image sources and rewrites media/ ones to bare file names."""

    @override
    def image(
        self,
        tokens: Sequence[Token],
        idx: int,
        options: OptionsDict,
        env: EnvType,
    ) -> str:
        token = tokens[idx]
        path = unquote(str(token.attrs.get("src", "")))
        if is_local(path):
            _media(env).add(path)
            if path.startswith(MEDIA_PREFIX):
                token.attrs["src"] = _basename(path)
        return super().image(tokens, idx, options, env)

    @override
    def html_inline(
        self,
        tokens: Sequence[Token],
        idx: int,
        options: OptionsDict,
        env: EnvType,
    ) -> str:
        return self._raw(tokens[idx].content, env)

    @override
    def html_block(
        self,
        tokens: Sequence[Token],
        idx: int,
        options: OptionsDict,
        env: EnvType,
    ) -> str:
        return self._raw(tokens[idx].content, env)

    @staticmethod
    def _raw(content: str, env: EnvType) -> str:
        def repl(match: re.Match[str]) -> str:
            path = unquote(html_lib.unescape(match.group(3)))
            if not is_local(path):
                return match.group(0)
            _media(env).add(path)
            if not path.startswith(MEDIA_PREFIX):
                return match.group(0)
            quote = match.group(2)
            return f"{match.group(1)}{quote}{html_lib.escape(_basename(path))}{quote}"

        return _RAW_SRC.sub(repl, content)


def _media(env: EnvType) -> set[str]:
    media = cast(set[str], env["media"])
    return media


_MD = MarkdownIt("commonmark", {"html": True})
_RENDERER = _MediaRenderer(_MD)


def render(text: str) -> tuple[str, set[str]]:
    """Render Markdown to HTML; return it with every local (non-URL) path it references."""
    env: EnvType = {"media": set()}
    tokens = _MD.parse(text, env)
    if [t.type for t in tokens] == ["paragraph_open", "inline", "paragraph_close"]:
        html = _RENDERER.renderInline(tokens[1].children or [], _MD.options, env)
    else:
        html = _RENDERER.render(tokens, _MD.options, env)
    return html.rstrip(), _media(env)
