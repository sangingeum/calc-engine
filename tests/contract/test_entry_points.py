"""Contract: declared console-script entry points.

Guards the packaging metadata for the Windows-safe alias (issue #12):
both ``calc`` and ``calcx`` must exist and bind to ``calc.cli:main``,
so a metadata edit can never silently drop the alias while every other
test stays green.
"""

from importlib.metadata import entry_points


def _calc_console_scripts() -> dict[str, str]:
    eps = entry_points(group="console_scripts")
    return {
        ep.name: ep.value
        for ep in eps
        if ep.name in ("calc", "calcx")
    }


def test_both_console_scripts_declared() -> None:
    eps = _calc_console_scripts()
    assert eps == {
        "calc": "calc.cli:main",
        "calcx": "calc.cli:main",
    }
