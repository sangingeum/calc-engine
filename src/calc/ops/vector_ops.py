"""Vector operations: strict JSON parsing + numpy math."""

from __future__ import annotations

import json

import numpy as np

from calc.errors import ArgumentError, MathError, SyntaxError_

_OPS = ("dot", "cross", "norm", "add", "subtract")


def _parse_vector(text: str) -> list[float]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SyntaxError_(f"invalid JSON vector: {exc}") from None
    if not isinstance(data, list) or not data:
        raise SyntaxError_("vector must be a non-empty JSON array of numbers")
    for cell in data:
        if isinstance(cell, bool) or not isinstance(cell, (int, float)):
            raise SyntaxError_("vector components must be numbers")
    return data


def vector(op: str, vectors: list[str]) -> object:
    """Apply a vector operation to one or two JSON vectors."""
    if op not in _OPS:
        raise ArgumentError(
            f"unknown vector operation: {op} (expected one of {', '.join(_OPS)})"
        )
    parsed = [[float(x) for x in _parse_vector(text)] for text in vectors]
    try:
        if op == "dot":
            if len(parsed) != 2:
                raise ArgumentError("dot requires exactly two vectors")
            return float(np.dot(parsed[0], parsed[1]))
        if op == "cross":
            if len(parsed) != 2:
                raise ArgumentError("cross requires exactly two vectors")
            if len(parsed[0]) != 3 or len(parsed[1]) != 3:
                raise MathError("cross requires two 3-dimensional vectors")
            return [float(x) for x in np.cross(parsed[0], parsed[1])]
        if op == "norm":
            if len(parsed) != 1:
                raise ArgumentError("norm requires exactly one vector")
            return float(np.linalg.norm(parsed[0]))
        if len(parsed) != 2:
            raise ArgumentError(f"{op} requires exactly two vectors")
        if len(parsed[0]) != len(parsed[1]):
            raise MathError("dimension mismatch between vectors")
        a, b = np.asarray(parsed[0]), np.asarray(parsed[1])
        result = a + b if op == "add" else a - b
        return [float(x) for x in result]
    except ValueError as exc:
        raise MathError(str(exc)) from None
