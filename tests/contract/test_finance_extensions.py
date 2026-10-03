"""finance extension contract: npv/irr/nper + sign-convention pinning."""

from __future__ import annotations

import math

import pytest
from conftest import run_calc


def test_npv_reference() -> None:
    # npf.npv(0.1, [-1000, 110, 121]) = -800 exactly (reference case)
    proc = run_calc("finance", "npv", "--rate", "0.1", "--cashflows", "[-1000,110,121]")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "-800.0000"


def test_irr_reference() -> None:
    # flows [-1000, 110, 121] never recover -> irr exists only as the
    # (mathematically present) negative root; numpy-financial returns it
    proc = run_calc("finance", "irr", "--cashflows", "[-1000,110,121]")
    assert proc.returncode == 0
    value = float(proc.stdout.strip())
    assert math.isfinite(value)


def test_irr_classic_reference() -> None:
    # -100 then +110 in one period: IRR = 10%
    proc = run_calc("finance", "irr", "--cashflows", "[-100,110]")
    assert proc.returncode == 0
    assert float(proc.stdout.strip()) == pytest.approx(0.10, abs=1e-6)


def test_irr_no_sign_change_is_matherror() -> None:
    proc = run_calc("finance", "irr", "--cashflows", "[100,110,121]")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("MathError: no real IRR found")
    assert proc.stderr.count("\n") == 1


def test_nper_reference() -> None:
    # paying -129.5046/period on a 1000 balance at 5% clears in 10 periods
    proc = run_calc(
        "finance", "nper", "--rate", "0.05", "--pmt", "-129.5046", "--pv", "1000"
    )
    assert proc.returncode == 0
    assert float(proc.stdout.strip()) == pytest.approx(10.0, abs=1e-3)


def test_nper_zero_rate_closed_form() -> None:
    proc = run_calc("finance", "nper", "--rate", "0", "--pmt", "-100", "--pv", "1000")
    assert proc.returncode == 0
    assert float(proc.stdout.strip()) == pytest.approx(10.0, abs=1e-9)


def test_legacy_ops_unchanged() -> None:
    proc = run_calc("finance", "fv", "--rate", "0.05", "--periods", "10", "--pv", "1000")
    assert proc.stdout.strip() == "-1628.8946"


def test_strict_arg_sets_hold_for_new_ops() -> None:
    proc = run_calc("finance", "npv", "--rate", "0.1", "--cashflows", "[1,2]", "--pmt", "1")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: finance npv requires exactly")
    assert "unexpected=['pmt']" in proc.stderr

    proc = run_calc("finance", "irr", "--cashflows", "[1,2]", "--rate", "0.1")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: finance irr requires exactly")


def test_cashflows_validation() -> None:
    proc = run_calc("finance", "npv", "--rate", "0.1", "--cashflows", "[100]")
    assert proc.returncode == 1
    assert proc.stderr.startswith("SyntaxError: cashflows must be a JSON array of >= 2")

    proc = run_calc("finance", "irr", "--cashflows", '[100,"x"]')
    assert proc.returncode == 1
    assert proc.stderr.startswith("SyntaxError: cashflows must contain only numbers")


def test_unknown_op_message_lists_new_ops() -> None:
    proc = run_calc("finance", "frobnicate", "--rate", "0.1")
    assert proc.returncode == 1
    assert "npv, irr, nper" in proc.stderr
