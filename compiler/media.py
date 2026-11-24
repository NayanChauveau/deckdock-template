"""The guard every media reference goes through before a file is read or copied."""

from pathlib import Path

MEDIA_DIR = "media"


def is_local(ref: str) -> bool:
    """Whether a reference designates a project file (not a URL or inline data)."""
    return bool(ref) and "://" not in ref and not ref.startswith(("//", "data:"))


def media_problem(root: Path, rel: str) -> str | None:
    """Return why the root-relative media path `rel` is unusable, or None if it is safe.

    The file must be a regular file whose resolved location (symlinks followed) lies
    inside the project's `media/` directory, itself inside the project.
    """
    if not rel.startswith(MEDIA_DIR + "/") or ".." in rel.split("/"):
        return f"media must live in media/ (got '{rel}')"
    path = root / rel
    try:
        if not path.exists() and not path.is_symlink():
            return f"missing media file '{rel}'"
        project = root.resolve()
        media_dir = (root / MEDIA_DIR).resolve()
        resolved = path.resolve()
        if not (
            media_dir.is_relative_to(project) and resolved.is_relative_to(media_dir)
        ):
            return f"media file '{rel}' resolves outside media/"
        if not resolved.is_file():
            return f"missing media file '{rel}'"
    except (OSError, RuntimeError) as exc:
        return f"cannot read media file '{rel}': {exc}"
    return None
