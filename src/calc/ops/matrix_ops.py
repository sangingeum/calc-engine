"""Matrix operations: strict JSON parsing + numpy math."""

from __future__ import annotations

import json

import numpy as np

from calc.errors import ArgumentError, MathError, SyntaxError_

_OPS = ("multiply", "add", "subtract", "inverse", "determinant", "transpose")


def _parse_matrix(text: str) -> list[list[float]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SyntaxError_(f"invalid JSON matrix: {exc}") from None
    if not isinstance(data, list) or not data or not all(isinstance(row, list) for row in data):
        raise SyntaxError_("matrix must be a non-empty JSON array of rows")
    width = len(data[0])
    if width == 0 or any(len(row) != width for row in data):
        raise SyntaxError_("matrix rows must all have the same length")
    for row in data:
        for cell in row:
            if isinstance(cell, bool) or not isinstance(cell, (int, float)):
                raise SyntaxError_("matrix cells must be numbers")
    return data


def matrix(op: str, matrices: list[str]) -> object:
    """Apply a matrix operation to one or two JSON matrices."""
    if op not in _OPS:
        raise ArgumentError(
            f"unknown matrix operation: {op} (expected one of {', '.join(_OPS)})"
        )
    parsed = [_parse_matrix(text) for text in matrices]
    try:
        if op == "multiply":
            if len(parsed) != 2:
                raise ArgumentError("multiply requires exactly two matrices")
            a, b = np.asarray(parsed[0]), np.asarray(parsed[1])
            return (a @ b).tolist()
        if op in ("add", "subtract"):
            if len(parsed) != 2:
                raise ArgumentError(f"{op} requires exactly two matrices")
            a, b = np.asarray(parsed[0]), np.asarray(parsed[1])
            result = a + b if op == "add" else a - b
            return result.tolist()
        if len(parsed) != 1:
            raise ArgumentError(f"{op} requires exactly one matrix")
        a = np.asarray(parsed[0])
        if op == "inverse":
            return np.linalg.inv(a).tolist()
        if op == "determinant":
            return float(np.linalg.det(a))
        return a.T.tolist()  # transpose
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise MathError(str(exc)) from None
