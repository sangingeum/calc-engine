# TASK-STAT-EXTENSION-SUMMARY.md

Date: 2026-09-21. Executor: athena (python-developer agent).
Governing spec: `/home/keum/.hermes/cache/documents/doc_fdfef6791813_calc-engine-extension-spec.md`
Dispatch: `TASK-stat-extension.md`.

## What was implemented

All required sections (1–15, 16, 20, 21, 22) of the spec:

- **stat extensions** (`src/calc/ops/stat_ops.py`): `covariance` (population
  default, `--ddof 1`), `pearson`, `spearman`, `regression` (OLS, fields:
  slope/intercept/r2/stderr/slope_stderr/residual_stderr/residual_variance),
  `quantile` (NumPy `linear`, h=(n-1)q), `rank` (1-based average ranks).
- **`distribution` command** (`src/calc/ops/distribution_ops.py`): 8 families
  (uniform, beta, normal, lognormal, exponential, gamma, binomial, poisson)
  × ops: mean, variance, stddev, skewness, kurtosis, excess-kurtosis, pdf,
  cdf, ppf, sample, validate, compare-moments. `describe` is intentionally
  rejected (`ArgumentError`) under the single-value stdout contract.
- **`assert` command** (`src/calc/ops/assert_ops.py`): approx (atol+rtol),
  equal, between (inclusive endpoints), sign (5 names), abs-lt, abs-gt.
  Failures are domain failures with a new `AssertionError:` stderr prefix,
  exit 1, empty stdout.
- CLI wiring in `src/calc/cli.py`; new `AssertionError` (subclass of
  `SyntaxError_`, prefix `AssertionError`) in `errors.py`.
- Backward compatibility: all pre-existing commands byte-identical; full
  original test suite passes unchanged (449 tests total, 0 failures).

## Documented conventions (also in SKILL.md / DESIGN.md §6b)

1. covariance: population by default (ddof=0), `--ddof 1` = sample.
2. ties: average ranks (deterministic).
3. quantile: NumPy `linear` interpolation, h = (n-1)*q.
4. regression stderr: `stderr` is an explicit alias of `slope_stderr`;
   `residual_stderr` = sqrt(SSR/(n-2)); `residual_variance` = SSR/(n-2).
5. kurtosis: non-excess (normal = 3); excess-kurtosis = kurtosis − 3.
6. sampling: numpy PCG64 (`np.random.default_rng(seed)`, numpy>=1.26,<2);
   `--seed` required; no implicit time source.
7. compare-moments: boolean stdout (`true`/`false`), two families, one
   `--moment` (mean|variance|stddev|skewness|kurtosis).
8. stdout contract: one value per run preserved everywhere; `describe`
   rejected rather than emitting structured output.

## Deferred

- §17 `stat bootstrap` and §18 statistical tests (ks, mann-whitney,
  permutation): optional; deferred as future work to keep the deterministic
  core stable first (permitted by the spec and the task dispatch).
- §19 Sobol/Saltelli: explicitly out of scope — not implemented.

## Test counts

- `uv run pytest -q` → **449 passed**, 0 failed, ~166 s.
- New files: `tests/unit/test_stat_extensions.py` (30 tests),
  `tests/unit/test_distribution_ops.py` (48 tests incl. §16 mandatory
  regression cases as parametrized set),
  `tests/contract/test_stat_extension_contract.py` (15 tests, incl. the
  named Beta(4.05,4.05) variance regression, bimodal two-point cases,
  stdout contract, stderr/exit-code, determinism tests).
- Lint/type gates: `uv run ruff check .` → clean;
  `uv run mypy src` → "Success: no issues found in 23 source files".
- Reference values are analytical (not implementation-vs-implementation):
  Beta(2,2) var 0.05; Beta(4.05,4.05) var 0.02747252747 / stddev
  0.165748…; Uniform(0,1) var 1/12; normal kurtosis 3; exponential
  skewness 2; Beta(2,2) kurtosis 15/7; pdf Beta(2,2) at 0.5 = 1.5;
  cdf(ppf(p)) ≈ p roundtrips; regression residual arithmetic verified by
  hand (SSR=0.7 case).

## Spec acceptance-criteria examples (§22) — real CLI output

```
=== §22.1 Beta mean/variance ===
0.5000
0.0500
=== §22.2 Beta(4.05,4.05) NOT variance 0.05 ===
0.02747252747        (--precision 11)
false                (compare-moments vs Beta(2,2), moment=variance, exit 0)
=== §22.3 Beta(2,2) variance 0.05 ===
true
=== §22.4 Uniform(0,1) moments ===
0.5000
0.08333333
0.2886751346
=== §22.5 two-point bimodal ===
[0.25,0.75]:   mean 0.5000, pvariance 0.0625
[0.2763932023,0.7236067977]: mean 0.5000, pvariance 0.05000000
=== §22.6 Pearson & Spearman ===
1.0000
-0.5000
=== §22.7 regression slope ===
2.0000
=== §22.8 signs and tolerances ===
true
true
=== §22.9 reproducible samples (twice, same seed) ===
[0.1486,0.7646,0.4182,0.5289,0.7776]
[0.1486,0.7646,0.4182,0.5289,0.7776]
=== §22.10 invalid parameters ===
MathError: uniform requires low < high   (exit 1)
=== §16 named regression: Beta(4.05,4.05) stddev ===
0.16574839
=== error contract sample ===
MathError: normal requires sigma > 0     (exit 1, empty stdout)
```

## Spec ambiguities resolved (decision input for the owner)

1. **`describe` rejected, not structured.** Spec §4 preferred separate
   mean/variance/stddev under the strict one-value contract; implemented as
   a typed `ArgumentError` so agents get an explicit signal instead of a
   contract violation.
2. **`compare-moments` boolean variant.** Spec §14 allowed "a boolean
   assertion interface"; implemented as `true`/`false` stdout for exactly
   two families × one moment, with the unsuffixed-flag tolerance
   (`--low/--high` style) accepted alongside `--low2/--high2` so the spec's
   example syntax parses as-is.
3. **`stderr` field naming.** Spec §1.4 preferred explicit
   `slope_stderr`/`residual_stderr`; both exposed, plus `stderr` kept as a
   documented alias of `slope_stderr` since the spec lists `stderr` as a
   possible field.
4. **Bimodal stddev discrepancy.** Spec §16 quotes stddev = 0.25 for
   {0.25, 0.75} with variance 0.0625 — that is the population stddev and
   sqrt(0.0625)=0.25 holds. The pre-existing `stat stdev` op is the SAMPLE
   stdev (ddof=1) = 0.3536; the population value is obtained via
   `stat pvariance` (verified = 0.0625). No code change was made; the
   distinction is documented here and in tests.
5. **New error prefix `AssertionError`.** The spec's error taxonomy does
   not name the failure type for `assert`; a distinct domain-failure prefix
   was added so failed assertions are distinguishable from usage errors
   (`ArgumentError`).
6. **`ppf` boundary.** `ppf(0)`/`ppf(1)` on continuous families yield
   ∓inf; `inf`/`-inf` rendering was already ratified in render.py.

## House-standards compliance

- All Python env management via `uv` (no global pip, PEP 668 respected).
- `ruff` clean (line-length 96, selected rules E/F/W/I/B/UP/SIM/BLE).
- `mypy src` clean.
- No other repos or agent profiles touched.

## Fix round (2026-09-21, per solomon's REVIEW R1/R2)

- **R1 done**: `pyproject.toml` now has `[tool.coverage.run] parallel = true`,
  `[tool.coverage.report] fail_under = 70, show_missing = true`. Vera's F1
  subprocess-coverage recipe (COVERAGE_PROCESS_START + parallel + combine)
  recorded in DESIGN.md §6a as the only sanctioned measurement method.
- **R2 done**: `_sample` in `src/calc/ops/distribution_ops.py` annotated
  `size: float | None, seed: float | None` (guards kept; annotations honest).
- N1–N3 left untouched per task directive.
- Verification (all real runs, this session):
  - `uv run pytest -q` → **449 passed** in 168.71s
  - `uv run ruff check .` → All checks passed!
  - `uv run mypy src` → Success: no issues found in 23 source files
  - Coverage (recipe): **TOTAL 92% (91.60%)**, gate `fail_under=70` reached —
    cli.py 82%, assert_ops.py 87%, distribution_ops.py 93%, stat_ops.py 93%.
  - Recipe-less `pytest --cov` control: cli.py 0%, TOTAL 74% — still above 70
    on this machine, but the 18-point CLI-layer loss shows why the recipe is
    the sanctioned method (DESIGN.md §6a).
- Not committed, per task directive.
