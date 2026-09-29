"""GitHub issue 11 (contract): `eval` accepts `ln` on stdout, typed on error.

`ln` is the natural-log alias of `log`; the failure path is the same typed
`MathError` line as every other domain error (exit 1, stderr only). The
already-consistent `sym`/`calculus` surfaces are asserted alongside so the
alias cannot silently diverge again.
"""

from __future__ import annotations

from conftest import run_calc


def test_eval_ln_stdout() -> None:
    proc = run_calc("eval", "ln(2)", "--precision", "6")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "0.693147\n"
    assert proc.stderr == ""


def test_eval_ln_invalid_domain_is_typed_error() -> None:
    proc = run_calc("eval", "ln(-1)")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("MathError: ")


def test_eval_ln_usable_in_compound_statement() -> None:
    proc = run_calc("eval", "x=ln(2)", "exp(x)", "--precision", "6")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "2.000000\n"


def test_other_expression_surfaces_accept_ln() -> None:
    proc = run_calc("sym", "equiv", "ln(x)", "log(x)", "--var", "x")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "true\n"

    proc = run_calc("calculus", "derive", "ln(x)", "--var", "x")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "1/x\n"
