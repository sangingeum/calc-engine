"""Uniform file / stdin input resolver (R3) — the ONLY fs/stdin access point.

INV-7: no other module may touch the filesystem or stdin. The resolver lives
in the CLI layer, never under ``calc.ops`` (a static unit test enforces this).

Token grammar (applied to every positional that carries data or text):

- ``@<path>``  read the file at ``<path>``
- ``@-``       read all of stdin
- ``@@<text>`` literal text ``@<text>`` (escape)
- anything else literal, unchanged

Modes: JSON/text arguments resolve to ``str`` (UTF-8); hash/crc/base64 data
resolves to ``bytes`` (raw, no decoding, no newline stripping).
"""

from __future__ import annotations

import stat as stat_module
import sys
from pathlib import Path

from calc.errors import ArgumentError

DEFAULT_MAX_INPUT_BYTES = 16 * 1024 * 1024  # 16 MiB


def _read_error(path: str, reason: str) -> ArgumentError:
    return ArgumentError(f"cannot read file '{path}': {reason}")


def _read_file_bytes(token: str, path_text: str, max_bytes: int) -> bytes:
    path = Path(path_text)
    try:
        info = path.stat()
    except OSError as exc:
        raise _read_error(path_text, exc.strerror or str(exc)) from None
    if not stat_module.S_ISREG(info.st_mode):
        raise _read_error(path_text, "not a regular file")
    if info.st_size > max_bytes:
        raise _read_error(
            path_text, f"file exceeds the {max_bytes}-byte input cap"
        )
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise _read_error(path_text, exc.strerror or str(exc)) from None
    if len(data) > max_bytes:  # size can change between stat and read
        raise _read_error(path_text, f"file exceeds the {max_bytes}-byte input cap")
    return data


def resolve_token(
    token: str, *, binary: bool = False, max_bytes: int = DEFAULT_MAX_INPUT_BYTES
) -> str | bytes:
    """Resolve one input token per the R3 grammar.

    ``binary=True`` returns raw file bytes for hash/crc/base64 inputs;
    otherwise the result is text (UTF-8 decoded for file/stdin sources).
    """
    if token.startswith("@@"):
        text = "@" + token[2:]
        return text.encode("utf-8") if binary else text
    if not token.startswith("@"):
        return token.encode("utf-8") if binary else token
    # '@' reference: '@-' is stdin, anything else is a path.
    path_text = token[1:]
    if path_text == "-":
        data = sys.stdin.buffer.read()
    else:
        data = _read_file_bytes(token, path_text, max_bytes)
    if len(data) > max_bytes:
        raise _read_error(token, f"input exceeds the {max_bytes}-byte cap")
    if binary:
        return data
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise _read_error(token, "file is not valid UTF-8") from None


def resolve_all(
    tokens: list[str] | None,
    *,
    binary: bool = False,
    max_bytes: int = DEFAULT_MAX_INPUT_BYTES,
) -> list[str | bytes] | None:
    """Resolve a list of tokens; enforce the single-``@-`` rule across them."""
    if tokens is None:
        return None
    stdin_count = sum(1 for t in tokens if t == "@-")
    if stdin_count > 1:
        raise ArgumentError("only one positional per invocation may be '@-' (stdin)")
    return [resolve_token(t, binary=binary, max_bytes=max_bytes) for t in tokens]
