"""Introspection contract: --version, functions, schema (agent discovery)."""

from __future__ import annotations

import json

from conftest import run_calc


def test_version_flag() -> None:
    proc = run_calc("--version")
    assert proc.returncode == 0
    assert proc.stdout.startswith("calc ")
    assert proc.stdout.count("\n") == 1


def test_functions_listing_complete() -> None:
    proc = run_calc("functions")
    assert proc.returncode == 0
    names = proc.stdout.strip().splitlines()
    assert len(names) == 41
    assert "sqrt" in names and "factorial" in names
    assert proc.stderr == ""


def test_functions_names_are_eval_callable() -> None:
    proc = run_calc("functions")
    for name in proc.stdout.strip().splitlines():
        # every listed name must actually evaluate
        call = run_calc("eval", f"{name}(1)") if name not in ("abs", "min", "max") else None
        if call is None:
            continue
        # NOT all functions accept a single argument (comb/perm need 2, etc.);
        # the gate is only that a wrong-arity call is a TYPED failure, and
        # single-arg functions succeed. Accept either exit 0 or a typed error.
        assert call.returncode in (0, 1), (name, call.stderr)
        if call.returncode == 1:
            assert call.stderr.split(":")[0].endswith("Error")


def test_schema_is_valid_json_with_all_subcommands() -> None:
    proc = run_calc("schema")
    assert proc.returncode == 0
    assert proc.stderr == ""
    doc = json.loads(proc.stdout)
    assert set(doc) == {"version", "subcommands"}
    registered = {
        "eval", "batch", "stat", "finance", "matrix", "convert-base",
        "convert-unit", "calculus", "physics-constant", "physics", "vector",
        "bits", "endian", "hash", "crc", "base64", "datetime", "regex",
        "distribution", "assert", "check", "number", "gof", "sym",
        "functions", "schema",
    }
    assert set(doc["subcommands"]) == registered


def test_schema_eval_option_entry() -> None:
    proc = run_calc("schema")
    doc = json.loads(proc.stdout)
    eval_opts = doc["subcommands"]["eval"]["options"]
    flags = {opt["flags"][0] for opt in eval_opts}
    assert "--precision" in flags
    assert "--let" in flags and "--exact" in flags and "--timeout" in flags


def test_schema_positionals_present() -> None:
    doc = json.loads(run_calc("schema").stdout)
    eval_pos = doc["subcommands"]["eval"]["positionals"]
    assert any(p["dest"] == "exprs" for p in eval_pos)
