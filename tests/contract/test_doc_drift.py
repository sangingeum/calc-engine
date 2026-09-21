"""Doc-drift guards (§5.3): SKILL.md must agree with the code."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "SKILL.md"


def _skill_text() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_eval_function_list_matches_registry():
    from calc.ops.eval_ops import _FUNCTION_NAMES

    text = _skill_text()
    match = re.search(
        r"\*\*Functions — the exhaustive list \((\d+)\):\*\*(.*?)(?=\n\n\*\*Constants)",
        text,
        re.DOTALL,
    )
    assert match, "eval function list header not found in SKILL.md"
    declared_count = int(match.group(1))
    section = match.group(2)
    listed = set(re.findall(r"`([a-z_0-9]+)`", section))
    registry = set(_FUNCTION_NAMES)
    assert declared_count == len(registry), (
        f"SKILL.md declares {declared_count} eval functions; registry has {len(registry)}"
    )
    assert listed == registry, (
        f"SKILL.md eval list drift: missing={sorted(registry - listed)} "
        f"extra={sorted(listed - registry)}"
    )


def test_distribution_family_table_matches_registry():
    from calc.ops.distribution_ops import _FAMILIES

    text = _skill_text()
    match = re.search(
        r"## distribution — probability distributions.*?(\n\| `)", text, re.DOTALL
    )
    assert match, "distribution family table not found in SKILL.md"
    section = text[match.start() : match.end() + 4000]
    section = section.split("Operations", 1)[0]
    listed = set(re.findall(r"^\| `([a-z0-9]+)` \|", section, re.MULTILINE))
    registry = set(_FAMILIES)
    assert listed == registry, (
        f"SKILL.md family table drift: missing={sorted(registry - listed)} "
        f"extra={sorted(listed - registry)}"
    )


def test_subcommand_count_and_list_matches_cli():
    import argparse

    from calc.cli import _build_parser

    text = _skill_text()
    frontmatter = text.split("---", 2)[1]
    match = re.search(r"(\d+) subcommands", frontmatter)
    assert match, "subcommand count not found in SKILL.md front matter"
    declared_count = int(match.group(1))

    parser = _build_parser()
    subactions = [
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    ]
    registered = set(subactions[0].choices)
    # The front matter lists the subcommands inside the parentheses after
    # "N subcommands"; extract exactly that list.
    list_match = re.search(r"\d+ subcommands \(([^)]*)\)", frontmatter)
    assert list_match, "subcommand list not found in SKILL.md front matter"
    listed = {name.strip() for name in list_match.group(1).split(",")}
    assert declared_count == len(registered), (
        f"SKILL.md front matter declares {declared_count} subcommands; "
        f"CLI registers {len(registered)}: {sorted(registered)}"
    )
    assert declared_count == len(listed), "declared count != listed count"
    missing = sorted(registered - listed)
    assert not missing, f"subcommands absent from SKILL.md front matter: {missing}"
    extra = sorted(listed - registered)
    assert not extra, f"front matter lists unregistered subcommands: {extra}"
