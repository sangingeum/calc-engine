# Changelog

All notable changes to calc-engine are documented here. The format follows
Keep a Changelog; the project does not guarantee semantic versioning for
pre-1.0 releases but bumps the minor version on behavior additions and the
patch version on fixes/docs.

## [0.2.0] — 2026-10-04

### Security and safety (P0)

- **Resource guards (`LimitError`)**: new error prefix for a tripped guard.
  Compute-side caps: `factorial/comb/perm` argument checks BEFORE computing
  (`factorial(10**7)` used to hang the process); expression-character cap
  (10000); result-digit cap (100000) applied to rendering. Wall-clock
  `--timeout SECONDS` (default 10, `0` disables) on
  `eval/batch/calculus/sym/physics/check`. Every cap is overridable via a
  `CALC_*` environment variable.
- **Result-rendering fix**: an integer/Fraction result beyond the int→str
  digit limit is now `LimitError: result exceeds 100000 digits` — previously
  such results (e.g. `2**20000`) died mid-render as a mislabeled
  `MathError: internal computation failure`.
- **Top-level exception hardening**: unexpected exceptions are
  `InternalError: <ExceptionType>: <first message line>` (one line, exit 1,
  never a traceback). `CALC_DEBUG=1` prints the traceback for diagnosis.
  KeyboardInterrupt still exits 130 silently.

### Behavior fixes (P0)

- **`calculus limit` is two-sided by default (`--dir +|-|both`)**. sympy's
  `limit()` defaults to the right-hand side, so
  `limit "1/x" --approach 0` silently reported `inf`; the default now
  requires both sides to agree, otherwise
  `MathError: limit does not exist (left=..., right=...)`. One-sided limits
  are explicit (`--dir +` → `inf`). **This is the only intentional
  default-output change in this release.**

### Performance

- **Lazy imports**: every invocation is a fresh process, so import time is
  user-visible. scipy/pint/sympy/numpy-backed ops modules load only in the
  handler that needs them. `calc eval "1+1"` cold start: ~0.80 s → ~0.08 s
  (10x); the full contract suite runs ~3.5x faster.

### New subcommands

- **`check`** — expression assertion for QA gates:
  `--actual EXPR --expected EXPR [--atol X] [--rtol X] [--strict]`. Prints
  `true`/`false` (exit 0 both — a false answer is a valid result);
  `--strict` turns false into a domain failure (`CheckFailed` prefix).
  `assert` (numeric literals only) is unchanged.
- **`number`** — number theory: `isprime` (deterministic < 2^64; beyond that
  a probable-prime result, documented), `nextprime`, `factorize`
  (`2^3*3^2*5`), `modinv` (no inverse → `MathError`), multi-argument
  `gcd`/`lcm`. Subject to the timeout and size guards.
- **`functions`** — list the eval function whitelist (41 names).
- **`schema`** — JSON catalog of every subcommand's positionals/options,
  generated from the argparse tree (agent self-discovery).

### Extended subcommands

- `datetime add` accepts whole calendar `--months`/`--years` with
  end-of-month clamping (Jan 31 + 1 month = Feb 28/29; fractional values are
  an `ArgumentError`); new `datetime business-days A B [--holidays '[...]']`
  counts Mon–Fri dates in the half-open range [A, B) minus holidays.
- `matrix` gains `solve` (square A × vector b; singular →
  `MathError: singular system`), `rank`, `trace`, `power`, `scale`,
  `identity`; dimension-mismatch errors name the operand shapes
  (`cannot multiply 2x2 by 1x3`).
- `stat` gains `percentile` (P in [0,100]), `multimode` (all modes, sorted —
  `mode` still returns the first only), `mad`, `range`, `zscore`.
- `finance` gains `npv`, `irr` (`--cashflows` JSON array; no sign change →
  `MathError: no real IRR found`), `nper` (zero-rate closed form). The
  numpy-financial sign convention (cash out negative) is now documented in
  README and SKILL.md with worked examples.

### Quality gates

- Security-input tests: attack shapes (dunder chains, `__import__`, `open`,
  `eval`, `exec`, lambda/comprehension DoS strings), malformed JSON, and a
  seeded bounded fuzz over `eval` inputs — every failure path stays inside
  the contract (exit 1, empty stdout, one typed stderr line, no traceback).
  Static gate: no `eval`/`exec`/`__import__` call sites in first-party
  source.
- Import-boundary tests pin the lazy-loading contract per subcommand.
- Error-contract regex extended with `LimitError`, `InternalError`,
  `CheckFailed`.

## [0.1.0] — initial public release

Subcommands: eval, batch, stat, finance, matrix, convert-base, convert-unit,
calculus, physics-constant, physics, vector, bits, endian, hash, crc, base64,
datetime, regex, gof, sym, distribution, assert. Byte-exact stdout contract,
typed single-line stderr, exit codes 0/1/2.
