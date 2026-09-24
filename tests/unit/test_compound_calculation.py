"""Compound calculations: multi-statement eval + stdin batch (design doc contract).

Covers: dependent chains, assignment-only input, mid-chain errors, ``==`` vs
``=``, single-statement backward compatibility, ``--precision`` applied only at
render time, ``-``-prefixed statements, and the stdin batch form.
"""

from __future__ import annotations

import pytest
from conftest import run_calc

from calc.errors import ArgumentError
from calc.ops import eval_ops

# ---------------------------------------------------------------------------
# Unit level: statement parsing and the compound engine
# ---------------------------------------------------------------------------


def test_split_assignment_standalone_equals_only():
    assert eval_ops._split_assignment("price = 12500") == ("price ", " 12500")
    assert eval_ops._split_assignment("2+2") is None
    assert eval_ops._split_assignment("a == b") is None
    assert eval_ops._split_assignment("a <= b") is None
    assert eval_ops._split_assignment("a >= b") is None
    assert eval_ops._split_assignment("a != b") is None
    # '=' inside a string literal is not an assignment
    assert eval_ops._split_assignment('x + "="') is None


def test_compound_dependent_chain():
    out = eval_ops._run_compound(
        ["price = 12500", "qty = 37", "subtotal = price * qty", "subtotal * 1.1"]
    )
    assert not out.had_error
    assert [(i, k) for i, k, _ in out.entries] == [(4, "value")]
    assert out.entries[0][2] == pytest.approx(508750.0)


def test_compound_assignment_only_prints_nothing():
    out = eval_ops._run_compound(["a = 2", "b = a * 3"])
    assert not out.had_error
    assert out.entries == ()


def test_compound_mid_chain_error_does_not_abort():
    out = eval_ops._run_compound(["a = 1", "a + 1/0", "a * 2", "a + 1"])
    assert out.had_error
    assert [(i, k, p) for i, k, p in out.entries] == [
        (2, "error", "MathError: division by zero"),
        (3, "indexed", 2),
        (4, "indexed", 2),
    ]


def test_compound_comparison_is_not_assignment():
    out = eval_ops._run_compound(["b = 5", "b * 2", "b == 5"])
    assert [(i, k) for i, k, _ in out.entries] == [(2, "indexed"), (3, "indexed")]
    assert not out.had_error


def test_compound_assignment_error_reports_slot():
    out = eval_ops._run_compound(["x = 1/0", "2+2"])
    assert out.had_error
    assert [(i, k, p) for i, k, p in out.entries] == [
        (1, "error", "MathError: division by zero"),
        (2, "value", 4),
    ]


def test_compound_invalid_target_and_shadowing():
    out = eval_ops._run_compound(["1bad = 2"])
    assert out.had_error
    assert out.entries[0][1] == "error"
    assert str(out.entries[0][2]).startswith("ArgumentError")
    out = eval_ops._run_compound(["sqrt = 2"])
    assert out.had_error
    assert str(out.entries[0][2]).startswith("ArgumentError")


def test_compound_full_precision_across_statements():
    # --precision is render-time only: the stored value must stay full precision
    out = eval_ops._run_compound(["third = 1/3", "third * 3"])
    assert out.entries[-1][2] == 1


def test_parse_statements_ignores_blanks_and_comments():
    text = "a = 1\n\n# comment\n  b = 2  \na * b\n"
    assert eval_ops.parse_statements(text) == ["a = 1", "b = 2", "a * b"]


def test_exact_rejects_compound_and_assignment():
    with pytest.raises(ArgumentError):
        eval_ops.eval_command(["2+2", "3*3"], exact=True)
    with pytest.raises(ArgumentError):
        eval_ops.eval_command(["a = 2"], exact=True)


# ---------------------------------------------------------------------------
# CLI contract level (subprocess, byte-exact stdout)
# ---------------------------------------------------------------------------


def test_cli_single_statement_backward_compat():
    proc = run_calc("eval", "2+2")
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "4\n", "")


def test_cli_compound_single_expression_result_is_bare():
    proc = run_calc("eval", "price=12500", "qty=37", "price*qty")
    assert (proc.returncode, proc.stdout) == (0, "462500\n")


def test_cli_compound_multiple_expression_results_indexed():
    proc = run_calc("eval", "a=2", "b=3", "a*b", "a**b")
    assert (proc.returncode, proc.stdout) == (0, "3: 6\n4: 8\n")


def test_cli_compound_assignment_only_empty_stdout():
    proc = run_calc("eval", "a=1", "b=2")
    assert (proc.returncode, proc.stdout, proc.stderr) == (0, "", "")


def test_cli_compound_mid_chain_error_slot_and_exit():
    proc = run_calc("eval", "a=1", "a+1/0", "a*2")
    assert proc.returncode == 1
    assert proc.stdout == "2: MathError: division by zero\n3: 2\n"


def test_cli_compound_precision_applies_at_render_only():
    proc = run_calc("eval", "third=1/3", "third*3", "--precision", "2")
    # stored value keeps full precision: 1/3 * 3 == 1 exactly; one expression
    # statement renders bare under the single-result contract
    assert (proc.returncode, proc.stdout) == (0, "1.00\n")


def test_cli_dash_prefixed_statements():
    for argv in (["eval", "-5+3"], ["eval", "--", "-5+3"]):
        proc = run_calc(*argv)
        assert (proc.returncode, proc.stdout) == (0, "-2\n"), argv


def test_cli_eval_vs_eq_and_shadowing():
    # a single expression statement renders bare, even with assignments present
    proc = run_calc("eval", "x=1", "x==1")
    assert (proc.returncode, proc.stdout) == (0, "1\n")
    # a single assignment statement keeps the legacy error contract (stderr)
    proc = run_calc("eval", "sqrt=2")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == "ArgumentError: assignment shadows a function/constant: 'sqrt'\n"
    # the same failure inside a compound reports the slot on stdout instead
    proc = run_calc("eval", "a=1", "sqrt=2")
    assert proc.returncode == 1
    assert proc.stdout == "2: ArgumentError: assignment shadows a function/constant: 'sqrt'\n"


def test_cli_batch_stdin_statements():
    import subprocess

    text = (
        "price = 12500\nqty = 37\n# subtotal\n\n"
        "subtotal = price * qty\nsubtotal\nsubtotal * 1.1\n"
    )
    proc = subprocess.run(
        ["uv", "run", "calc", "batch"],
        input=text,
        capture_output=True,
        text=True,
        check=False,
    )
    assert (proc.returncode, proc.stdout) == (0, "4: 462500\n5: 508750.0000\n")


def test_cli_batch_empty_stdin_is_argument_error():
    import subprocess

    proc = subprocess.run(
        ["uv", "run", "calc", "batch"],
        input="# only a comment\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr == "ArgumentError: batch: no statements on stdin\n"
