"""Matrix operations: strict JSON parsing + numpy math."""

from __future__ import annotations

import json

from calc.errors import ArgumentError, MathError, SyntaxError_

_OPS = (
    "multiply",
    "add",
    "subtract",
    "inverse",
    "determinant",
    "transpose",
    "solve",
    "rank",
    "trace",
    "power",
    "scale",
    "identity",
)


def _numpy():
    """numpy is resolved lazily: plain eval/stat calls must not pay for it."""
    import numpy as np

    return np


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


def _shape(matrix: list[list[float]]) -> str:
    return f"{len(matrix)}x{len(matrix[0])}"


def _parse_count(text: str, what: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise ArgumentError(f"{what} must be an integer (got {text!r})") from None
    if value < 0:
        raise MathError(f"{what} must be non-negative (got {value})")
    return value


def _require_square(matrix: list[list[float]], op: str) -> None:
    rows, cols = len(matrix), len(matrix[0])
    if rows != cols:
        raise MathError(f"{op} requires a square matrix (got {_shape(matrix)})")


def matrix(op: str, matrices: list[str]) -> object:
    """Apply a matrix operation to one or two JSON matrices (or scalars)."""
    if op not in _OPS:
        raise ArgumentError(
            f"unknown matrix operation: {op} (expected one of {', '.join(_OPS)})"
        )
    np = _numpy()

    # scalar-taking ops come first (their "matrices" list holds A + scalar)
    if op == "identity":
        if len(matrices) != 1:
            raise ArgumentError("identity takes exactly N")
        n = _parse_count(matrices[0], "N")
        return np.identity(n).tolist()
    if op == "scale":
        if len(matrices) != 2:
            raise ArgumentError("scale takes exactly MATRIX and K")
        parsed = [_parse_matrix(matrices[0])]
        try:
            k = float(matrices[1])
        except ValueError:
            raise ArgumentError(
                f"scale factor must be a number (got {matrices[1]!r})"
            ) from None
        return (np.asarray(parsed[0]) * k).tolist()
    if op == "power":
        if len(matrices) != 2:
            raise ArgumentError("power takes exactly MATRIX and N")
        parsed = [_parse_matrix(matrices[0])]
        _require_square(parsed[0], "power")
        n = _parse_count(matrices[1], "exponent N")
        try:
            return (np.linalg.matrix_power(np.asarray(parsed[0]), n)).tolist()
        except (ValueError, np.linalg.LinAlgError) as exc:
            raise MathError(str(exc)) from None

    if op == "solve":
        if len(matrices) != 2:
            raise ArgumentError("solve requires exactly MATRIX and VECTOR")
        square = _parse_matrix(matrices[0])
        _require_square(square, "solve")
        rhs = _parse_vector(matrices[1])
        a = np.asarray(square)
        if len(rhs) != a.shape[0]:
            raise MathError(
                f"solve shape mismatch: matrix {_shape(square)} vs vector of {len(rhs)}"
            )
        try:
            return [float(x) for x in np.linalg.solve(a, np.asarray(rhs))]
        except np.linalg.LinAlgError as exc:
            raise MathError(f"singular system: {exc}") from None

    parsed = [_parse_matrix(text) for text in matrices]
    try:
        if op == "multiply":
            if len(parsed) != 2:
                raise ArgumentError("multiply requires exactly two matrices")
            a, b = np.asarray(parsed[0]), np.asarray(parsed[1])
            if a.shape[1] != b.shape[0]:
                raise MathError(
                    f"cannot multiply {_shape(parsed[0])} by {_shape(parsed[1])}"
                )
            return (a @ b).tolist()
        if op in ("add", "subtract"):
            if len(parsed) != 2:
                raise ArgumentError(f"{op} requires exactly two matrices")
            if _shape(parsed[0]) != _shape(parsed[1]):
                raise MathError(
                    f"cannot {op} {_shape(parsed[0])} with {_shape(parsed[1])}"
                )
            a, b = np.asarray(parsed[0]), np.asarray(parsed[1])
            result = a + b if op == "add" else a - b
            return result.tolist()
        if op == "solve":  # unreachable: handled above (vector second operand)
            raise ArgumentError("solve requires exactly MATRIX and VECTOR")
        if len(parsed) != 1:
            raise ArgumentError(f"{op} requires exactly one matrix")
        a = np.asarray(parsed[0])
        if op == "inverse":
            _require_square(parsed[0], "inverse")
            return np.linalg.inv(a).tolist()
        if op == "determinant":
            _require_square(parsed[0], "determinant")
            return float(np.linalg.det(a))
        if op == "rank":
            return int(np.linalg.matrix_rank(a))
        if op == "trace":
            return float(np.trace(a))
        return a.T.tolist()  # transpose
    except (ValueError, np.linalg.LinAlgError) as exc:
        raise MathError(str(exc)) from None
