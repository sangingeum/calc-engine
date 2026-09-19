"""Regex operations over the ``re`` module (Python dialect only).

The standard ``re`` engine has no timeout, so matching runs in a short-lived
subprocess with a hard wall-clock limit — catastrophic backtracking turns into
a clean timeout error instead of a hang. ``test`` returning False is a normal
result (exit 0); only an invalid pattern is a SyntaxError. Python dialect only
in v1 (``--flavor`` reserves the slot for future engines like ecma).
"""

from __future__ import annotations

import json
import subprocess
import sys

from calc.errors import ArgumentError, MathError, SyntaxError_

_TIMEOUT_SECONDS = 2.0

_FLAVORS = frozenset({"python"})

_FLAG_BITS: dict[str, int] = {
    "i": 2,  # re.IGNORECASE
    "m": 8,  # re.MULTILINE
    "s": 16,  # re.DOTALL
    "x": 64,  # re.VERBOSE
    "a": 256,  # re.ASCII
}


def _resolve_flavor(flavor: str | None) -> str:
    if flavor is None:
        return "python"
    if flavor not in _FLAVORS:
        raise ArgumentError(f"unknown regex flavor: {flavor!r} (expected python)")
    return flavor


def _resolve_flags(flags: str | None) -> int:
    if flags is None:
        return 0
    unknown = sorted(set(flags) - set(_FLAG_BITS))
    if unknown:
        raise ArgumentError(
            f"unknown regex flag(s): {''.join(unknown)!r} (expected subset of imsx + a)"
        )
    value = 0
    for char in flags:
        value |= _FLAG_BITS[char]
    return value


def _run_worker(payload: dict[str, object]) -> object:
    """Execute the match in a subprocess with a hard timeout (backtracking guard)."""
    code = (
        "import json, re, sys\n"
        "payload = json.loads(sys.stdin.read())\n"
        "pattern = payload['pattern']\n"
        "subject = payload['subject']\n"
        "flags = payload['flags']\n"
        "op = payload['op']\n"
        "compiled = re.compile(pattern, flags)  # invalid pattern -> SyntaxError here\n"
        "if op == 'test':\n"
        "    out = compiled.search(subject) is not None\n"
        "elif op == 'findall':\n"
        "    out = compiled.findall(subject)\n"
        "elif op == 'groups':\n"
        "    match = compiled.search(subject)\n"
        "    out = list(match.groups()) if match else []\n"
        "else:  # sub\n"
        "    out = compiled.sub(payload['replacement'], subject)\n"
        "print(json.dumps(out))\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MathError(
            f"regex exceeded {_TIMEOUT_SECONDS:g}s execution budget (possible "
            "catastrophic backtracking)"
        ) from exc
    if proc.returncode != 0:
        if "re.error" in proc.stderr or "error at position" in proc.stderr:
            raise SyntaxError_(f"invalid regex pattern: {payload['pattern']!r}")
        raise MathError(f"regex worker failed: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def regex(
    op: str,
    pattern: str,
    subject: str,
    *,
    flags: str | None = None,
    flavor: str | None = None,
    replacement: str | None = None,
) -> bool | list[str | tuple[str, ...]] | str:
    """Regex test/findall/groups/sub; Python dialect only (v1)."""
    if op not in ("test", "findall", "groups", "sub"):
        raise ArgumentError(
            f"unknown regex operation: {op!r} (expected test|findall|groups|sub)"
        )
    _resolve_flavor(flavor)
    if op == "sub":
        if replacement is None:
            raise ArgumentError("regex sub requires --replacement")
        if r"\1" in replacement or r"\g" in replacement or r"\0" in replacement:
            # keep it simple in v1: no backreference expansion
            raise ArgumentError("backreferences in --replacement are not supported in v1")
    result = _run_worker(
        {
            "op": op,
            "pattern": pattern,
            "subject": subject,
            "flags": _resolve_flags(flags),
            "replacement": replacement or "",
        }
    )
    if op == "test":
        # lower-case literals keep the stdout contract JSON/JSONL-friendly
        return "true" if result else "false"
    return result  # type: ignore[return-value]
