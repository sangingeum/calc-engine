# Gate doc — TASK-CALC-V2: calc-engine verification-backend extension (R1-R12)

- **Implementing agent:** Athena (python-developer)
- **Date:** 2026-09-21
- **Baseline:** `main` @ `5206a52`, 449 passing tests
- **Spec:** calc-engine — Requirements Specification: Verification-Backend Extensions (v2), doc_618466a04690
- **Status:** Implementation complete for R1-R12; awaiting vera/solomon gating.

## What shipped per requirement

| Req | Title | Status | Notes |
|---|---|---|---|
| R1 | `hash` `@path` not silently hashed | DONE | hash/crc/base64 accept `@file` as raw bytes; `@@` escape; typed `ArgumentError: cannot read file ...` on failure; B1 regression test |
| R2 | args beginning with `-` | DONE | argv preprocessing in cli.py (`_normalize_positionals`); eval/assert/regex/hash verified; `--` still works; B2 fixed |
| R3 | uniform file/stdin resolver | DONE | `src/calc/input_resolver.py` (sole fs/stdin module); applies to stat/matrix/vector/regex/gof/sym (text) and hash/crc/base64 (raw bytes); `@-` stdin, single-`@-` rule, regular files only, 16 MiB cap + `--max-input-bytes`; static INV-7 guard test; B4 fixed |
| R4 | correlation significance | DONE | `--field coefficient\|p\|t\|df\|n`, `--alternative two-sided\|greater\|less`; pinned t-approximation (df = n-2); `stat critical-r --n --alpha` (0.126666 @ n=240, α=0.05); scipy cross-checks incl. ties @ 1e-9 |
| R5 | `sf` operation | DONE | All 11 families via `dist.sf` (not 1−cdf); `sf normal 8` → `6.221e-16`; sf+cdf≈1 property test |
| R6 | t, chi2, kumaraswamy | DONE | Closed-form `_Kumaraswamy`; all ops incl. seeded `sample` (inverse-CDF, literal-pinned); `allow_abbrev=False` fixes B3/B6; undefined→`MathError: moment undefined`, infinite→`inf` |
| R7 | gof ks / chi2 / chi2-bins | DONE | `--field` required; KS = `kstest(..., method='auto')` (pinned); B7-style sum-match, support and n/K≥5 checks; scipy cross-checks; beta-sample sanity test (seed 42) |
| R8 | eval special functions + `--let` | DONE | erf/erfc/gamma/lgamma/comb/perm + abs/min/max/round; `--let NAME=NUMBER` numeric literals only, shadowing rejected; B5 fixed |
| R9 | `distribution fit` | DONE | Closed forms for beta/gamma/normal/lognormal/uniform with exact spec bounds/messages; kumaraswamy → `ArgumentError`; roundtrip property tests |
| R10 | `sym` equiv/simplify/expand | DONE | Restricted sympy path; decimals as exact rationals; fixed rational test grid (documented in SKILL.md); `MathError: undecided` otherwise |
| R11 | `eval --exact` | DONE | Fraction recursive-descent parser; `-7/16`, `1/2`, `1/4` pinned; inexact → `MathError`; `--exact` + `--precision` → `ArgumentError` |
| R12 | stat skewness/kurtosis | DONE | Population (biased) moments, non-excess kurtosis; pinned 1.1384/2.7880/−0.2120; large-sample normal property test |

Appendix B defects B1-B6: all closed with regression tests.

## Test counts

- Baseline suite (`5206a52`): 449 passed — unchanged, all still green (INV-4).
- New tests: 78 (Phase 1 contract: 15, Phase 2 unit: 31, Phase 3 unit: 22, doc-drift: 3, plus fit/roundtrip/sanity additions).
- **Final: 527 passed, 0 failed** (`uv run pytest -q`).

## Gates

- `uv run pytest -q` → 527 passed
- `uv run ruff check src tests` → All checks passed
- `uv run mypy src` → Success: no issues found in 26 source files
- `uv run pip-audit` → No known vulnerabilities found
- Coverage: `fail_under = 70` retained in pyproject.toml; vera's §6a recipe should be used to re-measure (per DESIGN.md 6a, plain `--cov` under-reports the CLI layer).

## Docs updated in the same change

- SKILL.md: 21 subcommands in front matter, 40-function exhaustive eval list, 11-family distribution table, new gof/sym/input-resolver/sf/fit/critical-r/skewness sections, pinned scipy/numpy versions (scipy 1.17.1, numpy 1.26.4 in uv.lock), RNG-stream caveat.
- README.md: Security notes rewritten per §5.4 (resolver-only file access, `--let` numeric literals, restricted sym parsing, no eval/exec).
- DESIGN.md: §5 Security notes extended; new §5b recording v2 design decisions.
- Doc-drift test (`tests/contract/test_doc_drift.py`): eval function list/count vs registry, distribution family table vs registry, subcommand count/list vs registered subparsers — fails on disagreement.

## Flagged judgment calls (verbatim to review)

1. **INV-7 static guard vs regex worker**: `regex_ops.py` legitimately contains `sys.stdin` inside its sandboxed subprocess payload string (pre-existing design). The static test bans `open(`/`pathlib` outright and permits `sys.stdin` only in that exact worker line.
2. **R3 scope**: resolver applied to `stat/matrix/vector/regex/gof/sym` positionals plus hash/crc/base64 data. `convert-unit`/`datetime` positionals untouched (numeric/unit semantics, not data/text — flagged in case review disagrees).
3. **`gof chi2` expected-count validation**: expected counts ≤ 0 are rejected (`MathError`); spec only mandates sum-match. Sum-match uses a 1e-9 relative tolerance rather than exact equality (float counts).
4. **`sym equiv` "false" path**: "differs by >1e-9 at any test point" returns `false` even when sympy cannot prove it; `true` additionally requires `diff.is_zero is True` after the grid passes, else `MathError: undecided`. Grid is fixed and documented (INV-5).
5. **R8 `round`**: Python banker's rounding (documented in SKILL.md); spec listed it as optional.
6. **`stat critical-r`**: rejects `--field` (spec did not define a field list for critical-r; it prints the single value). One-sided uses the 1−α t quantile.
7. **`--let` duplicate-name rejection** and `--exact` identifier rejection implemented stricter than spec text (spec silent on both).
8. **`distribution` parser gained `--mean/--variance/--field(fit_param)`**: the fit field is stored as `fit_param` internally to avoid clashing with stat semantics; other ops unaffected.
9. **`gamma`/`lgamma` int surfacing**: wrapped to return `int` when the result is integral (so `gamma(5)` renders `24`, not `24.0000`), preserving the bare-integer stdout convention.
10. **R9 dispatch order**: `fit` is dispatched before `_scipy_dist(params)` so fit never requires the family's distributional flags (`--alpha` etc.).
11. **Pin status**: numpy 1.26.4 / scipy 1.17.1 are what `uv.lock` resolves to; SKILL.md states them next to the `sample` determinism note. The lock file pins transitively; no `[tool.uv]` constraint-values were added beyond pyproject's existing `numpy>=1.26,<2`.

## Remaining gaps / recommendations for the gate

- Coverage percentage should be re-measured with the DESIGN.md 6a recipe.
- R4 optional Fisher-z CI fields (`ci_lower`/`ci_upper`, P2) were not implemented (spec-optional).
- `sym equiv` may return `MathError: undecided` for provable-but-hard identities where sympy's `is_zero` is unknown and the grid is uninformative — this is the spec-mandated behavior but callers should be aware.
