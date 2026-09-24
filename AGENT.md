# calc-engine

Deterministic, subcommand-driven CLI math engine for AI agents. Python 3.11+,
uv-managed, packaged via `uv_build` (console script `calc = calc.cli:main`).

## Layout

- `src/calc/cli.py` — argparse parser, subcommand dispatch (`_handlers`),
  input resolver glue, error→stderr mapping, and the single stdout writer.
- `src/calc/ops/` — pure domain modules (`eval_ops`, `stat_ops`,
  `distribution_ops`, ...). Ops never touch fs/stdin (resolver is CLI-layer
  only, enforced by a static test).
- `src/calc/errors.py` — typed error taxonomy (`CalcError` base with a class
  `prefix` mapped to stderr: MathError, SyntaxError, ValueError,
  ArgumentError, AssertionError).
- `src/calc/render.py` — value→stdout rendering (`--precision` applies at
  render only).
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
- `eval` supports compound statements (expressions + `name = expr`
  assignments, shared names dict, render-time precision); `batch` reads
  newline-separated statements from stdin.
