"""GitHub issue 8: integer-valued results render as integers, not X.0000.

df/n (stat pearson|spearman, gof chi2|chi2-bins) and --let bindings made of
integer literals must render bare (6, 8, 3), per the bare-integer stdout
convention already kept by `eval "-2+5"`, `gamma(5)`, `comb(5,2)`.
Float bindings/results stay float (a*b with a=2.5 -> 5.0000).
"""

from __future__ import annotations

from conftest import run_calc


def test_stat_pearson_df_and_n_integer() -> None:
    x, y = "[1,2,3,4,5,6,7,8]", "[2,1,4,3,6,5,8,7]"
    proc = run_calc("stat", "pearson", x, y, "--field", "df")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "6\n"
    proc = run_calc("stat", "pearson", x, y, "--field", "n")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "8\n"


def test_stat_spearman_df_and_n_integer() -> None:
    x, y = "[1,2,3,4]", "[4,3,2,1]"
    proc = run_calc("stat", "spearman", x, y, "--field", "df")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "2\n"
    proc = run_calc("stat", "spearman", x, y, "--field", "n")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "4\n"


def test_gof_chi2_df_integer() -> None:
    proc = run_calc("gof", "chi2", "[18,22,20,20]", "[20,20,20,20]", "--field", "df")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "3\n"


def test_eval_let_integer_bindings_render_bare() -> None:
    proc = run_calc("eval", "a*b", "--let", "a=2", "--let", "b=3")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "6\n"
    proc = run_calc("eval", "a+b", "--let", "a=1", "--let", "b=2")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "3\n"


def test_eval_let_negative_integer_binding() -> None:
    proc = run_calc("eval", "a+b", "--let", "a=-3", "--let", "b=1")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "-2\n"


def test_eval_let_float_stays_float() -> None:
    proc = run_calc("eval", "a*b", "--let", "a=2.5", "--let", "b=2")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "5.0000\n"
    proc = run_calc("eval", "a", "--let", "a=2.0")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "2.0000\n"


def test_eval_let_exponent_literal_is_float() -> None:
    proc = run_calc("eval", "a", "--let", "a=2e0")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "2.0000\n"
