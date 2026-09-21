# Two-axis review — calc-engine v2 (R1-R12), 5206a52..ac55093

Reviewer: Solomon. Date: 2026-09-21. Independent verification: 527 passed
(fresh run, 194s), ruff clean, mypy clean, ~60 live CLI probes across all
R1-R12 paths. Verdict: **changes-requested** (1 blocking finding).

## Blocking

1. **[blocking] `distribution skewness kumaraswamy` returns the raw third
   central moment, not standardized skewness.**
   `src/calc/ops/distribution_ops.py` — `_Kumaraswamy.stats('s')` returns
   `_central_moment(3)` directly; scipy's `.stats(moments='s')` contract (which
   `_moment()` relies on) is *standardized* skewness mu3/sigma^3.
   Observed: `calc distribution skewness kumaraswamy --a 2 --b 2` → `-0.0013544974`.
   Correct value (exact sympy integration and closed-form raw moments agree):
   `-0.1253034159`. Kurtosis path is correct (verified: 2.1800472255 exact).
   This is a silently wrong number emitted by a verification tool — the exact
   P0 hazard class this spec exists to eliminate. Not caught because Appendix A
   pins only kumaraswamy mean/variance/cdf/ppf. Fix: return
   `_central_moment(3)/var()**1.5` in `stats('s')` (and pin the value in a test).

## Non-blocking findings

2. [non-blocking] R2 regression: glued option form `--precision=6` no longer
   parses for `eval` (baseline 5206a52 accepted it, printed 4). Repro:
   `calc eval "2+2" --precision=6` → `ArgumentError: unrecognized arguments:
   --precision=6`. `_normalize_positionals` classifies options by exact
   option-string only, so `--precision=6` falls into positionals after the
   expression and `parse_known_args` rejects it. Space-separated form still
   works. Fix direction: split `--opt=value` tokens in the option scan.
3. [non-blocking] INV-2 breach on huge `--exact` results: `calc eval
   "2**10000000" --exact` dies with a 14-line ValueError traceback from
   `Fraction.__str__` (CPython 4300-digit int→str limit) inside `render()`,
   which sits *outside* the `except Exception` guard in `cli.main`. Exit 1,
   but stderr is not one typed line. Fix direction: wrap the render/print in
   the same defensive handler, or pre-check digit count in `_evaluate_exact`.
4. [non-blocking, undisclosed spec deviation] R6: spec mandates "t mean for
   df ≤ 1 ⇒ `MathError: moment undefined`". Implementation renders `inf` for
   `mean t --df 1` and pins that in `test_r6_t_moment_undefined_and_infinite`
   (line 248-249). Mathematically the Cauchy mean is undefined, not +inf.
   Either fix the df==1 mean case or amend the spec/SKILL.md with the recorded
   deviation — it is not among the 11 flagged judgment calls.
5. [non-blocking] `base64 decode @file` on non-UTF-8 bytes surfaces as
   `MathError: internal computation failure` (generic catch-all), because the
   strict re-decode in `hash_ops.base64_code` raises outside the resolver's
   typed-UTF-8 error path. Typed but uninformative; route through an
   ArgumentError naming the file.
6. [non-blocking] `--input hex` + `@file` on hash/crc: `raw_bytes` silently
   wins, so the file is hashed as raw bytes rather than parsed as hex.
   Defensible (file bytes are the point) but the interaction is undocumented;
   add one line to SKILL.md or reject the combination.
7. [non-blocking] INV-7 static guard only globs `src/calc/ops/*.py` (top
   level). Adequate today (flat layout), but a nested package would escape the
   guard; consider `rglob("*.py")`.

## Disposition of the 11 flagged judgment calls

1. regex worker `sys.stdin` exemption — ACCEPT. Exemption is scoped to the
   exact payload line plus comments; guard otherwise strict.
2. convert-unit/datetime excluded from resolver — ACCEPT. Spec §R3 enumerates
   the covered positionals; these aren't data/text-bearing.
3. chi2 expected>0 rejected; sum-match at 1e-9 rel — ACCEPT. scipy would emit
   inf/nan p-values otherwise; typed MathError is the better contract.
4. equiv "false" on grid evidence, "undecided" otherwise — ACCEPT. Grid is
   fixed, documented in SKILL.md, INV-5 clean; false positives impossible
   (nonzero at any point proves nonzero).
5. `round` = banker's — ACCEPT, documented in SKILL.md.
6. critical-r rejects `--field`; one-sided uses 1−α quantile — ACCEPT, matches
   spec formula.
7. `--let` duplicates and `--exact` identifiers rejected — ACCEPT, both are
   safe-direction strictness.
8. fit field stored as `fit_param` — ACCEPT; no stat/distribution clash.
9. gamma/lgamma int surfacing — ACCEPT, preserves bare-integer convention.
10. fit dispatched before `_scipy_dist` — ACCEPT (required, else fit would
    demand family flags).
11. pin via uv.lock only — ACCEPT.

## Axis summaries

**Spec axis:** R1-R12 all present with pinned acceptance values verified live
(-2+5=3; @file raw bytes; spearman/pearson p=0.002008 df=6 n=8; critical-r
0.1267; sf normal 8 = 6.221e-16; t cdf/ppf; kumaraswamy mean 0.5333; gof
0.0929/0.940242; erf 0.842701; --let; fit 2.0000; --exact -7/16; stat mean @-
= 2.5000; skewness 1.1384). Doc-drift tests structurally compare registry vs
SKILL.md and would fail on disagreement. One silent correctness bug (finding
1) and one undisclosed deviation (finding 4). Fisher-z CI correctly skipped
(spec-optional). No scope creep observed.

**Standards axis:** Python checklist clean — mypy/ruff/pip-audit green
(verified), types complete, pathlib used, errors via typed taxonomy (no new
prefixes, INV-3 ok), PEP 668 respected (uv throughout). INV-1/INV-2 verified
across ~60 probes except finding 3. `_normalize_positionals` and
`_subparser_option_map` reach into `parser._actions` private API — judgement
call, acceptable for a CLI shim but fragile across argparse versions; a
comment noting that dependency exists. Test quality good: behavior-pinned,
scipy cross-checks at 1e-9, regression tests per Appendix B defect.
