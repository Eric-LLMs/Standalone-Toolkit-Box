"""Utility functions for executable detection and path resolution."""

import os
import re
import shutil
from pathlib import Path


def find_executable(name: str, fallback_paths: list[str]) -> str | None:
    """Locate an executable by name, with hardcoded fallback paths.

    Returns the absolute path to the executable, or ``None`` if not found.
    """
    path = shutil.which(name)
    if path:
        return os.path.abspath(path)
    for fb in fallback_paths:
        if os.path.isfile(fb):
            return os.path.abspath(fb)
    return None


def resolve_path(base_dir: str | Path, *segments: str) -> str:
    """Join *segments* relative to *base_dir* and normalise the result."""
    return os.path.normpath(os.path.join(str(base_dir), *segments))


def sanitize_name(text: str, max_len: int = 80) -> str:
    """Turn *text* into a safe folder name.

    Replaces illegal characters and strips leading/trailing whitespace
    and dots. Truncates to *max_len* characters.
    """
    # Replace characters that are illegal on Windows / problematic cross-platform
    sanitised = re.sub(r'[<>:"/\\\\|?*]', "_", text)
    # Collapse multiple underscores/spaces
    sanitised = re.sub(r"_{2,}", "_", sanitised)
    sanitised = re.sub(r"\s{2,}", " ", sanitised)
    # Trim leading/trailing whitespace, dots, hyphens
    sanitised = sanitised.strip(" .-")
    # Truncate
    if len(sanitised) > max_len:
        sanitised = sanitised[:max_len].rstrip(" .-")
    return sanitised or "untitled"
