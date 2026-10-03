# calc-engine

Deterministic, subcommand-driven CLI math engine for AI agents. Python 3.11+,
uv-managed, packaged via `uv_build` (console scripts `calc` and `calcx`,
both `calc.cli:main` — `calcx` is the Windows-safe alias, since
`C:\Windows\System32\calc.exe` is on PATH there).

## Layout

- `src/calc/cli.py` — argparse parser, subcommand dispatch (`_handlers`),
  input resolver glue, error→stderr mapping, and the single stdout writer.
- `src/calc/ops/` — pure domain modules (`eval_ops`, `stat_ops`,
  `distribution_ops`, ...). Ops never touch fs/stdin (resolver is CLI-layer
  only, enforced by a static test). The package resolves its modules
  LAZILY: scipy/pint/sympy/numpy-backed modules load only in the handler
  that needs them (cold-start contract, tested).
- `src/calc/errors.py` — typed error taxonomy (`CalcError` base with a class
  `prefix` mapped to stderr: MathError, SyntaxError, ValueError,
  ArgumentError, AssertionError, LimitError, InternalError, CheckFailed).
- `src/calc/limits.py` — resource guards: result-digit / factorial / comb /
  expression-length caps and the wall-clock timeout; each constant
  overridable via a `CALC_*` env var; guards run before computing.
- `src/calc/render.py` — value→stdout rendering (`--precision` applies at
  render only; digit-limit overflow is a LimitError).
- `src/calc/input_resolver.py` — the only fs/stdin access point (`@file`,
  `@-`, `@@escape`, 16 MiB cap).
- `tests/unit`, `tests/contract` — pytest; `tests/conftest.py` runs `calc`
  as a subprocess for byte-exact contract tests.

## Commands

- Test: `uv run pytest -q -W error` (warn-clean is the house bar).
- Lint: `uv run ruff check src tests` (line length 96); types:
  `uv run mypy src`.
- Run locally: `uv run calc <subcommand> ...`.
- Contract: SKILL.md front matter must declare the exact subcommand list
  (drift test: `tests/contract/test_doc_drift.py`).

## Principles

- Byte-exact stdout on success (result only); exactly one typed stderr line
  on failure; exit 0 success / 1 domain failure / 2 usage.
- `simpleeval` only — never Python `eval`/`exec`.
- Resource guards run BEFORE computing: a pathological request is a typed
  `LimitError` in microseconds, never a hang.
- Ops modules are pure and lazy-loaded; version + docs live in CHANGELOG.md
  (release notes) and DESIGN.md (design decisions).
- `eval` supports compound statements (expressions + `name = expr`
  assignments, shared names dict, render-time precision); `batch` reads
  newline-separated statements from stdin.
