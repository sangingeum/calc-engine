"""Shared helper: invoke the installed ``calc`` console script as a subprocess."""

from __future__ import annotations

import subprocess


def run_calc(*args: str) -> subprocess.CompletedProcess[str]:
    """Invoke calc via uv in the project environment; UTF-8 text capture."""
    return subprocess.run(
        ["uv", "run", "calc", *args],
        capture_output=True,
        text=True,
        check=False,
    )
