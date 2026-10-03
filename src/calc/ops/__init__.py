"""Pure domain modules: no I/O, no sys.stdout/stderr/sys.exit.

Every module raises CalcError subclasses; rendering and exiting are cli.py's
job alone (DESIGN.md boundary rule).

Modules are imported LAZILY via module __getattr__: every invocation is a
fresh process, and eagerly importing all ops modules pulls scipy.stats /
pint / sympy / numpy into even a plain `calc eval 1+1` (~0.7s of import
time). With lazy access, `calc eval` imports only eval_ops (simpleeval).
Static import scanning (tests/contract/test_v2_phase1_contract.py, and
tests/test_lazy_imports.py) must use the lazy proxy carefully — the public
access path remains `from calc.ops import x_ops`.
"""

from __future__ import annotations

import importlib

_MODULES = (
    "assert_ops",
    "base_ops",
    "bits_ops",
    "calculus_ops",
    "check_ops",
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
)

__all__ = list(_MODULES)


def __getattr__(name: str):  # noqa: ANN202 - module-level proxy
    """Lazily import an ops module on first attribute access."""
    if name in _MODULES:
        return importlib.import_module(f"calc.ops.{name}")
    raise AttributeError(f"module 'calc.ops' has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(_MODULES))
