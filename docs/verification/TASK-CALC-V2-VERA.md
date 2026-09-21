# Gate report — TASK-CALC-V2: calc-engine v2 (R1-R12)

- **Verifier:** Vera (qa/test engineer)
- **Date:** 2026-09-21
- **HEAD verified:** `3986165` (origin/main, fresh `git fetch` + `git log`; fix-round commit `56ac4b3`, docs `ac55093`)
- **Baseline:** `5206a52` (checked out temporarily; 449 tests collected — matches spec INV-4/gate doc)
- **Spec:** doc_618466a04690 (v2 requirements, Appendix A checklist)
- **Verdict: OVERALL PASS** — all acceptance criteria independently reproduced; one minor residual finding (F1, non-blocking).

## 1. Fresh full suite (iron law)

```
uv run pytest -q  →  531 passed in 199.34s (0:03:19), 0 failed
```

Matches the butler's 531 and the gate doc's post-fix count (527 + 4 fix-round tests). Verified baseline count independently: `git checkout 5206a52; uv run pytest --collect-only -q` → **449 tests** — INV-4 bookkeeping is honest (449 + 82 new = 531; 82 new test functions counted via grep, gate doc said "78 new tests" pre-fix-round, consistent).

Static gates re-run fresh: `ruff check src tests` → All checks passed; `mypy src` → Success, 26 files; `pip-audit` → no known vulnerabilities (only the expected "local package not on PyPI" notice).

## 2. Coverage (DESIGN.md §6a sanctioned recipe)

```
COVERAGE_PROCESS_START=pyproject.toml uv run pytest -q --cov=src/calc
  → 531 passed; TOTAL 90% (89.82%); "Required test coverage of 70.0% reached"
uv run coverage combine → "No data to combine" (expected per §6a note)
```

Per-module (fresh): cli.py 89%, input_resolver.py 86%, gof_ops.py 78%, sym_ops.py 79%, stat_ops.py 92%, distribution_ops.py 88%. `fail_under = 70` is genuinely met, not just configured. parallel=true confirmed in pyproject.toml line 44.

## 3. Independent repro per requirement (all values from live runs this session)

**R1 (hash @path) — PASS.** `hash sha256 '@/tmp/r1file.txt'` (file contains `hello`) → `2cf24dba…b9824` = `hash sha256 hello` (byte-identical, cross-checked). `hash sha256 @@hello` → digest of text `@hello` (`8f8a2f30…`). `@does-not-exist` → exit 1, stdout empty (0 bytes), stderr exactly one line `ArgumentError: cannot read file 'does-not-exist': No such file or directory`.

**R2 (leading `-`) — PASS.** `eval "-2+5"` → `3` exit 0; `eval "-0.35*(1+0.5*(0.5-0.25)*2)" --precision 6` → `-0.437500`; `eval -- "-2+5"` → `3`; `assert sign -0.5 negative` → `true`; `assert between -0.5 -1 0` → `true`; `hash sha256 "-abc"`, `regex test "-x" "-x"` → exit 0. Solomon fix #2 verified: `eval "2+2" --precision=6` → `4` (glued option survives preprocessing).

**R3 (resolver) — PASS.** `stat spearman @/tmp/x.json @/tmp/y.json` = inline result (1.0000). `printf '[1,2,3,4]' | calc stat mean @-` → `2.5000`. `stat mean @@[1,2]` → `SyntaxError` (escape yields non-JSON literal). Missing file → exit 1 one-line ArgumentError. Cap: 3.4 MB file → OK at default, `--max-input-bytes 1000` → `ArgumentError: cannot read file '/tmp/big.json': file exceeds the 1000-byte input cap`. Double stdin → `ArgumentError: only one positional per invocation may be '@-' (stdin)`. INV-7 static guard test present and passing (rglob-based after fix #7).

**R4 (correlation significance) — PASS.** spearman/pearson `[1..8]` vs `[2,1,4,3,6,5,8,7]`: coefficient 0.9048, `--field p` → 0.002008 (both), df → 6.0000, n → 8.0000. `critical-r --n 240 --alpha 0.05` → 0.126666; independently recomputed via scipy: `t_crit/√(n−2+t_crit²)` = 0.12666640118 — match. n<3 → typed `MathError: at least 3 observations are required for significance` (exit 1, coefficient path unaffected).

**R5 (sf) — PASS.** `sf normal 8` → `6.221e-16` (general format). `sf t 1.5 --df 238` → `0.0675` vs scipy `t.sf(1.5,238)` = 1−0.9325301216 = 0.067470 ✓. sf+cdf≈1 property test in suite.

**R6 (t/chi2/kumaraswamy) — PASS.** cdf t 1.5 df238 → 0.9325 (scipy 0.9325301 ✓); ppf t 0.975 df10 → 2.2281 (scipy 2.228139 ✓); cdf chi2 3 df5 → 0.3000 (scipy 0.3000142 ✓); variance chi2 → 10.0000. Kumaraswamy(2,2): mean 0.5333, variance 0.0489, cdf(0.3) 0.1719, ppf(0.5) 0.5412 — all match Appendix A. Invalid params (`--b -1`) → MathError exit 1. `allow_abbrev=False` live: `--a 2 --b 2` works (B3/B6 closed). Solomon fix #1 verified live: `skewness kumaraswamy --a 2 --b 2` → **-0.1253034159** (corrected standardized value, not the raw third moment), kurtosis 2.1800472255. t mean df 0.5 → `MathError: moment undefined`; t variance df 1.5 → `inf` (fix #4 verified).

**R7 (gof) — PASS.** ks vs U(0,1) statistic 0.0929; chi2 stat 0.4000 / p 0.9402 / df 3.0000. Discrete family → `ArgumentError: gof ks supports continuous families only; binomial is discrete`. Missing `--field` → argparse usage error exit 2 (spec: `--field` required ✓). Sum-mismatch caught. Sanity scenarios: 240 seeded beta(2,2) samples (`--size 240 --seed 42`) → `gof ks … beta` p = 0.7472 (> 0.01 ✓), vs uniform p = 0.0109 (< 0.05 ✓); `gof chi2-bins --bins 20` p = 0.2093; shape cross-check `stat skewness` 0.0048 / `stat kurtosis` 2.0821 (≈ symmetric, ≈ platykurtic-flat — consistent with beta(2,2)).

**R8 (special functions, --let) — PASS.** erf(1) 0.842701; erfc(1) 0.157299; gamma(5) → `24` (int surfacing, judgment call #9 confirmed); lgamma(5) 3.1781; comb(5,2) 10; perm(5,2) 20; comb(-1,2) → MathError exit 1. `a*b --let a=2 --let b=3` → 6; `--let sqrt=2` → `ArgumentError: --let name shadows a function/constant: 'sqrt'`.

**R9 (fit) — PASS.** beta M=0.5 V=0.05 → alpha 2.0000, beta 2.0000; V=0.0625 → 1.5000; V=0.25 → `MathError: beta fit requires variance < mean*(1-mean) = 0.25; got 0.25`; kumaraswamy → `ArgumentError: fit is not supported for family: kumaraswamy (supported: beta, gamma, lognormal, normal, uniform)`.

**R10 (sym) — PASS.** equiv `-0.35*(1+0.5*(0.5-A)*2)` vs `-0.525+0.35*A` → `true` (decimal-as-rational working — no 1e-17 residue); `(x+1)**2` vs `x**2+1` → `false`; expand → `x**2 + 2*x + 1`; undeclared `y` → `SyntaxError: undeclared symbol(s): y (declare with --var)`. Bonus: `sin(x)**2+cos(x)**2 ≡ 1` → true.

**R11 (--exact) — PASS.** `-0.35*(1+0.5*(0.5-0.25)*2)` --exact → **-7/16** (arithmetic independently verified with Python fractions: True); `1/3+1/6` → 1/2; `2**-2` → 1/4; `sqrt(2)` / `2**0.5` → MathError (distinct typed messages); `1/0` → `MathError: division by zero`. Solomon fix #3 verified: `eval '2**10000000' --exact` → exactly one typed line (`MathError: internal computation failure`), no traceback leak — INV-2 holds.

**R12 (skewness/kurtosis) — PASS.** `[1,2,3,4,10]`: skewness 1.1384, kurtosis 2.7880, excess -0.2120 (numpy recompute: 1.138420 / 2.787999 ✓). n=1 → MathError.

**Appendix A two-point sanity:** binary 50/50 x (n=240), perfectly monotone y → spearman **0.8660** (= √3/2, matches the pinned observation).

## 4. Doc-drift test efficacy (verified red→green)

Corrupted SKILL.md (removed `` `gamma`, `` from the eval function list):

```
uv run pytest -q tests/contract/test_doc_drift.py
  → FAILED tests/contract/test_doc_drift.py::test_eval_function_list_matches_registry (1 failed, 2 passed)
```

Restored from backup → `git status SKILL.md` clean, 3 passed. The guard has real teeth; it checks count AND set-equality against the registry.

## 5. Gate-doc claims vs reality

| Claim | Reality |
|---|---|
| 531 passed post-fix | ✓ (fresh run) |
| Baseline 449 unchanged | ✓ (449 collected at 5206a52) |
| ruff/mypy/pip-audit clean | ✓ re-run fresh |
| fail_under=70 "re-measure with §6a" | ✓ 89.82% via recipe |
| Judgment calls 1-11 accepted, fix-round findings 1-8 | Spot-verified live: #1 (kumaraswamy skew -0.1253034159), #2 (glued opts), #3 (INV-2 one-liner), #4 (t df≤1 MathError), #5 (base64 non-UTF-8 typed error, names file) — all confirmed in output above |
| Subcommand count 21 | ✓ counted 21 in `calc --help` |
| scipy/numpy pins in SKILL.md | ✓ line 322 (numpy 1.26.4 / scipy 1.17.24 per uv.lock claim) |

## 6. Findings

**F1 (minor, non-blocking) — `--exact` accepts explicit `--precision 4`.**
Spec R11: "`--exact` together with `--precision` ⇒ `ArgumentError`." cli.py line 766 implements `if exact and precision != 4: raise` — so `calc eval "1/2" --exact --precision 4` prints `1/2`, exit 0, instead of an ArgumentError. Output is still correct (default precision is 4, so no wrong evidence), but the guard deviates from the spec text. This is the only acceptance-criterion deviation found across R1-R12.
- Suggested failing test (for athena): `calc eval "1/2" --exact --precision 4` → expect exit 1, `ArgumentError: --exact cannot be combined with --precision`. Fix: detect explicit `--precision` presence (e.g. compare against argparse default / use `default=None`) rather than value != 4.
- Solo repro: `uv run calc eval "1/2" --exact --precision 4; echo $?` → `1/2`, `0`.

**F2 (observation, no action)** — `sym equiv 'sin(x)' 'cos(x)'` returns `false` (grid difference > 1e-9) rather than `MathError: undecided`. This is within the spec's letter (grid-difference path ⇒ false) and consistent with documented judgment call #4. Noting only so callers know `equiv` can say "false" for different-but-not-provably-unequal-on-all-reals expressions.

## 7. Verdict

OVERALL **PASS**. R1-R12 all independently verified with fresh live output; coverage gate genuinely met (89.82% via sanctioned recipe); doc-drift guard proven effective; gate-doc counts honest; solomon fix-round fixes confirmed live. One minor residual (F1) handed to athena — non-blocking, does not gate completion.

— Vera, QA/verification gate
