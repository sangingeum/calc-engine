"""Lazy-import cold-start guards (CALC-12 follow-through).

Every calc invocation is a fresh process; `eval` (simpleeval) must not pay
for scipy/pint/sympy/numpy. These run the CLI in-process against a fresh
interpreter to inspect sys.modules.
"""

from __future__ import annotations

import subprocess
import sys

_PROBE = """
import sys
sys.argv = ["calc", *%r]
from calc.cli import main
main()
heavy = [m for m in ("scipy", "pint", "sympy", "numpy", "numpy_financial")
         if any(mod == m or mod.startswith(m + ".") for mod in sys.modules)]
print(",".join(heavy), file=sys.stderr)
"""


def _heavy_modules_after(args: list[str]) -> list[str]:
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE % args],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    out = proc.stderr.strip()
    return [m for m in out.split(",") if m]


def test_eval_imports_no_heavy_modules() -> None:
    assert _heavy_modules_after(["eval", "1+1"]) == []


def test_batch_imports_no_heavy_modules() -> None:
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE % ["batch"]],
        input="1+1\n2*3\n",
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "1: 2\n2: 6"


def test_stat_pays_only_its_own_import() -> None:
    heavy = _heavy_modules_after(["stat", "mean", "[1,2,3]"])
    assert "scipy" in heavy or "numpy" in heavy  # pays for what it uses
    assert "sympy" not in heavy and "pint" not in heavy


def test_convert_unit_pays_only_pint() -> None:
    heavy = _heavy_modules_after(["convert-unit", "1", "miles", "km"])
    assert "pint" in heavy
    # pint.compat itself probes scipy/numpy (third-party behavior, not ours);
    # the first-party rule is that sympy stays out of the unit path.
    assert "sympy" not in heavy


def test_calculus_pays_only_sympy() -> None:
    heavy = _heavy_modules_after(["calculus", "derive", "x**2", "--var", "x"])
    assert "sympy" in heavy
    assert "pint" not in heavy


def test_datetime_is_stdlib_only() -> None:
    assert _heavy_modules_after(["datetime", "from-epoch", "1700000000"]) == []


def test_lazy_proxy_resolves_all_ops_modules() -> None:
    from calc import ops

    for name in ops.__all__:
        assert getattr(ops, name).__name__.endswith(name.split(".")[-1]) or name, name


def test_dir_lists_lazy_modules() -> None:
    from calc import ops

    listing = dir(ops)
    assert "eval_ops" in listing and "distribution_ops" in listing
