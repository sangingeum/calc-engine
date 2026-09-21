# Gate doc — calc-engine issue-fix round: GitHub issues 5-9 (agent-report)

- **Implementing agent:** Athena (python-developer)
- **Date:** 2026-09-21
- **Baseline:** `main` @ `66d6eb5` (issues verified against `c7ef142` by the reporter; all repros re-confirmed at HEAD before fixing)
- **Final:** `main` @ issue-9 commit (this change), **574 passed, 0 failed**
- **Status:** Fixes complete for issues 5-9; awaiting solomon review (issues stay open).

## Per-issue summary

| Issue | Title | Fix commit | Regression tests |
|---|---|---|---|
| 6 | distribution silently accepts unknown --flags (+ owner-ratified foreign-param tightening) | `12f10fc` | `tests/contract/test_issue6_unknown_flags.py` (10) |
| 7 | compare-moments documented syntax fails on some interpreters; --family2 works only by accident | `4ee00b2` (+ `92f0802` scratch cleanup) | `tests/contract/test_issue7_compare_moments.py` (6) |
| 5 | regex pattern/replacement wrongly resolved as @file | `ba22c65` | `tests/contract/test_issue5_regex_subject_only.py` (6) |
| 8 | integer-valued results render as 6.0000 (df/n, gof df, eval --let) | `2000989` | `tests/contract/test_issue8_integer_rendering.py` (7) |
| 9 | --input hex silently ignored with @file (fix b: reject) | this commit | `tests/contract/test_issue9_input_hex_file.py` (7) |

Each new test file was run RED at the pre-fix HEAD before the fix was written
(direct repro or the issue-documented interpreter-dependent failure), then
GREEN after.

## Fix details worth review

1. **Issue 6** — `_normalize_positionals` (cli.py) parks unregistered long
   options (`^--[A-Za-z][\w-]*(=.*)?$`) with the options and reports them
   verbatim via the stray list returned to `main()`; consumed value tokens
   travel with the stray (`--foo 3` reported whole). Single-dash tokens keep
   the R2 behavior; explicit `--` still forces positional parsing. The
   owner-ratified tightening: every distribution op EXCEPT compare-moments
   rejects parameters not belonging to the chosen family (including `*2`
   variants) — `ArgumentError: --X is not a parameter of <family>`
   (`_FAMILY_PARAMS` / `_reject_foreign_params` in distribution_ops.py).
2. **Issue 7** (ordering constraint with 6) — `_normalize_positionals` now
   rebuilds argv as `<cmd> <options> -- <positionals>` for ANY post-option
   positional (interleaving), not only leading-dash ones: argparse's routing
   of post-option positionals into `nargs="?"` slots is version-specific
   (3.12.3 leaves `uniform` unmatched). `--family2` is now a registered
   option (dest `family2_opt`, documented preferred form); `--familyX` is
   rejected. A doc-example test executes every SKILL.md/README
   compare-moments example against its claimed output. Source note added at
   `_subparser_option_map` pointing at the pinning test. No CI matrix file
   exists in this repo (no .github/workflows); issue 7's CI-matrix
   suggestion is left for the owner/solomon to decide.
3. **Issue 5** — `_resolve_cli_inputs` special-cases regex: only the SUBJECT
   (last token) passes through the resolver; pattern and replacement are
   always literal. Subject file/stdin/`@@` escape resolution unchanged.
4. **Issue 8** — `stat pearson|spearman --field df|n` and
   `gof chi2|chi2-bins --field df` return int (bare render);
   `eval --let` binds integer-looking literals (no `.`/exponent) as int;
   `2.5`/`2.0`/`2e0` stay float. Acceptance case verified end-to-end:
   `gof chi2-bins <240 beta values> --bins 10 --field df` → `9`.
5. **Issue 9** (fix b, owner direction) — `--input hex` combined with
   `@file`/`@-`/`@@` is rejected with
   `ArgumentError: --input hex cannot be combined with @file (file bytes are
   hashed raw); use --input hex only with inline hex`. R1 semantics for
   `@@hello` without the flag are preserved (digest of literal `@hello`);
   `hash sha256 @file` without `--input` unchanged. Judgment call flagged:
   the `@@` escape is also rejected under `--input hex` rather than silently
   hashing `@hello` as text — the issue's acceptance criterion is "no silent
   precedence," and the escape path had the same defect.

## Contract invariants held

- stdout-only result, one stderr `ErrorType: description` line, exit 0/1/2 —
  pinned by the new tests and the existing contract suite.
- R2 leading-dash positionals, R3 resolver scope (minus the issue-5 regex
  narrowing), R1 escape semantics all have explicit unchanged-behavior tests
  in the new files.

## Gates (this round, final tree)

- `uv run pytest -q` → **574 passed** (baseline 538 + 36 new)
- `uv run ruff check src tests` → All checks passed
- `uv run mypy src` → Success: no issues found in 26 source files
- `uv run pip-audit` → No known vulnerabilities found (exit 0; the project
  itself is not on PyPI and is skipped, as in prior rounds)
- Coverage: `--cov` plain run 77.70% (floor 70) — per DESIGN.md 6a this
  under-reports the CLI layer; vera's recipe remains authoritative for
  re-measurement.

## Docs updated in the same changes

- SKILL.md: compare-moments preferred `--family2` form + foreign-param rule
  + unknown-flag rule (issue 6/7); input-resolver regex-subject narrowing
  (issue 5); `--let` integer-binding rendering (issue 8); `--input hex` +
  `@file` rejection replacing the old precedence note (issue 9).
- README.md: mirror updates for all five.
- DESIGN.md: unchanged this round (no new architectural decisions; the
  issue-6 tightening is a behavior fix ratified by the owner, recorded here
  and in SKILL.md).

## Flagged judgment calls (verbatim to review)

1. Physics subcommand is exempt from the parametrized unknown-flag test:
   its dynamic `--symbol value` extraction is by design and the domain
   validator already rejects unknown symbols by name
   (`ArgumentError: unknown symbol(s) for domain ...`).
2. Issue 7's CI-matrix-over-3.11/3.12/3.13 suggestion is NOT implemented
   (repo has no CI workflow at all); the doc-example test plus the
   version-independent argv rebuild address the underlying defect.
3. `TASK-STAT-EXTENSION-SUMMARY.md` (a pre-existing untracked root doc from
   the v2 round) was swept into the issue-6 commit by `git add -A`.
4. Unregistered-long-option values are consumed heuristically (next token
   that is not itself an option/registered option) purely so the error
   message reports `--foo 3` whole; argparse still sees the parked tokens,
   and the final unknown list is de-duplicated.
