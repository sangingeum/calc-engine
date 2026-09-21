"""Pure domain modules: no I/O, no sys.stdout/stderr/sys.exit.

Every module raises CalcError subclasses; rendering and exiting are cli.py's
job alone (DESIGN.md boundary rule).
"""

from calc.ops import (
    assert_ops,
    base_ops,
    bits_ops,
    calculus_ops,
    datetime_ops,
    distribution_ops,
    eval_ops,
    finance_ops,
    gof_ops,
    hash_ops,
    matrix_ops,
    parse_utils,
    physics_ops,
    regex_ops,
    stat_ops,
    sym_ops,
    sympy_real,
    unit_ops,
    vector_ops,
)

__all__ = [
    "assert_ops",
    "base_ops",
    "bits_ops",
    "calculus_ops",
    "datetime_ops",
    "distribution_ops",
    "eval_ops",
    "finance_ops",
    "gof_ops",
    "hash_ops",
    "matrix_ops",
    "parse_utils",
    "physics_ops",
    "regex_ops",
    "stat_ops",
    "sympy_real",
    "sym_ops",
    "unit_ops",
    "vector_ops",
]
