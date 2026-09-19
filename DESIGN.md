# DESIGN.md — calc-engine

Design document for `calc`, a deterministic, subcommand-driven CLI math engine
for AI agents. Written against the requirements doc
(`~/.hermes/cache/documents/doc_2d100997a3b8_computation_CLI_for_agents._Overview._Overview.md`).
This is a design-only document; no implementation is included.

## 1. Architectural Overview

Single-process, single-entry-point Python CLI. The contract with the calling
agent is byte-exact:

- stdout: ONLY the result. A number or a string, no labels, no banners, no
  trailing commentary. A trailing newline is the only permitted decoration.
- stderr: on failure, exactly one line of the form `ErrorType: description`.
- exit code: 0 on success, non-zero (1) on any failure.

Pattern: **command-dispatch + exception-boundary**. Every subcommand resolves
to a pure function that returns a value; all failure paths funnel through one
top-level exception boundary that maps domain exceptions to the error taxonomy
(§4). No command ever writes to stdout itself — the entry point is the sole
writer.

```
            ┌─────────────────────────────────────┐
            │  main (entry point)                 │
            │  parse args → dispatch → render     │
            └───────┬──────────────────┬──────────┘
              dispatch             exception boundary
            ┌───────▼──────┐    ┌────────▼─────────┐
            │ subcommand   │    │ CalcError tree   │
            │ handlers     │    │ → stderr + exit 1│
            └───────┬──────┘    └──────────────────┘
                    │ pure compute, return value
            ┌───────▼──────────────────────────────┐
            │ domain modules (no I/O)              │
            │ eval_ops / stat_ops / finance_ops /  │
            │ matrix_ops / base_ops / unit_ops /   │
            │ calculus_ops / physics_ops           │
            └──────────────────────────────────────┘
```

Boundary rule: domain modules raise `CalcError` subclasses and never touch
`sys.stdout`/`sys.stderr`/`sys.exit`. Rendering and exit are the entry point's
job alone. This is what makes the whole suite testable without subprocesses.

## 2. Repo Layout

```
calc-engine/
├── DESIGN.md
├── README.md                  # usage + agent-integration contract (stdout/stderr/exit codes)
├── pyproject.toml             # uv-managed; deps per spec §2
├── uv.lock
├── src/
│   └── calc/
│       ├── __init__.py        # version only
│       ├── __main__.py        # python -m calc
│       ├── cli.py             # entry point: parse, dispatch, render, exception boundary
│       ├── errors.py          # CalcError taxonomy (§4)
│       ├── render.py          # result → stdout formatting (precision, plain output)
│       └── ops/
│           ├── __init__.py
│           ├── eval_ops.py        # simpleeval backend
│           ├── stat_ops.py        # statistics stdlib (numpy fallback not required)
│           ├── finance_ops.py     # numpy-financial
│           ├── matrix_ops.py      # numpy + strict JSON parse
│           ├── base_ops.py        # int(val, base) / format()
│           ├── unit_ops.py        # pint
│           ├── calculus_ops.py    # sympy (derive/integrate/limit)
│           ├── physics_ops.py     # scipy.constants + sympy.Eq/solve solvers
│           └── vector_ops.py      # numpy
└── tests/
    ├── conftest.py
    ├── contract/              # end-to-end via subprocess: stdout-only, stderr, exit codes
    │   ├── test_stdout_contract.py
    │   └── test_error_contract.py
    └── unit/                  # per-op module tests, no subprocess
        └── test_<op>.py
```

Install as a package (`uv init --lib` or packaged layout) so the console
script `calc` exists; agents will call `calc <subcmd>` from any cwd.

## 3. Module Breakdown

### 3.1 cli.py — routing

**Choice: argparse, not typer.** Reasoning:

- The CLI is fully specified and stable in the requirements doc; we gain
  nothing from typer's type-hint magic, and argparse ships in stdlib — one
  fewer runtime dependency and one fewer failure mode (typer pulls click, whose
  version churn has broken CLIs before).
- The spec itself says "the implementer may use argparse or typer" — argparse
  is explicitly sanctioned.
- argparse gives precise control over `--from` (a Python keyword) via
  `parser.add_argument("--from", dest="from_base")` without special-casing.

Subcommand map (argparse subparsers, `required=True`):

| Subcommand | Handler | Backend |
|---|---|---|
| `eval <expr> [--precision N]` | `eval_ops.evaluate` | simpleeval (no eval/exec — see §5) |
| `stat <op> <dataset>` | `stat_ops.stat` | `statistics` stdlib |
| `finance <op> [--pv --fv --rate --periods --principal]` | `finance_ops.finance` | numpy-financial |
| `matrix <op> <matrices...>` | `matrix_ops.matrix` | numpy + `json.loads` |
| `convert-base <value> --from B --to B` | `base_ops.convert` | `int(value, base)` + format |
| `convert-unit <value> <from> <to>` | `unit_ops.convert` | pint |
| `calculus <op> <expr> --var V [--lower --upper --approach]` | `calculus_ops.calculus` | sympy |
| `physics-constant <symbol>` | `physics_ops.constant` | scipy.constants |
| `physics <domain> --solve V [--dynamic kwargs]` | `physics_ops.solve` | sympy.Eq/sympy.solve |
| `vector <op> <vectors...>` | `vector_ops.vector` | numpy |

Dynamic `physics` kwargs (`--v0, --t, --a, --m, --f, ...`): argparse
`parse_known_args` or an explicit per-domain option list. Design decision: use
an explicit registry — each domain (kinematics/force/energy) declares its
equation set and accepted symbols. Unknown `--foo` is an ArgumentError, not a
silent ignore. This keeps `--solve` targets strictly validated and error
messages actionable.

### 3.2 render.py

- Floats: format to `--precision` (default 4) decimal places via
  `f"{x:.{p}f}"`-style fixed formatting; strip nothing else. Integer results
  (matrix determinant of ints? no — always numeric string) are rendered as
  plain numbers; booleans never appear on stdout.
- Convert-base results are plain strings (`1010`, `ff` — see §6 gap on case).
- sympy results: converted to floats when numeric (precise), or stringified
  with `str(sympy_expr)` only when symbolic output is inherent (limit at
  infinity, symbolic integrate without bounds).
- Determinism: no locale-dependent formatting; set formatting explicitly.

### 3.3 Error taxonomy (errors.py)

```python
class CalcError(Exception): ...          # base, never raised directly
class MathError(CalcError): ...          # invalid math: div-by-zero, bad matrix dims
class SyntaxError_(CalcError): ...       # bad input formatting: bad expr, invalid JSON
class UnitError(CalcError): ...          # unsupported unit/constant (maps to ValueError: prefix)
class ArgumentError(CalcError): ...      # missing/extra variables, bad operation choice
```

The class names deliberately differ from the built-ins; the *stderr prefix*
string is stored per class (e.g. `UnitError.prefix == "ValueError"`), so we
never shadow `SyntaxError`/`ValueError` and never build messages by hand at
raise sites.

cli.py boundary:

```python
try:
    result = handler(args)
except CalcError as e:
    print(f"{type(e).__prefix__}: {e}", file=sys.stderr)
    sys.exit(1)
except Exception:  # defensive: unknown crash must NOT leak a traceback to stdout
    print("MathError: internal computation failure", file=sys.stderr)
    sys.exit(1)
print(render(result))   # sole stdout writer in the entire program
```

Notes:
- argparse itself exits 2 with usage text on bad args — that already satisfies
  "non-zero + stderr"; wrap or accept as-is (spec doesn't pin the code, only
  non-zero). Accepted as-is; documented in README.
- KeyboardInterrupt/BrokenPipeError handled separately (exit 130 / silent).

## 4. Test Strategy

Two layers, mirroring the two guarantees (correct math, strict contract):

1. **Contract tests (subprocess-level)** — the non-negotiables:
   - stdout contains exactly one line (result) for a battery of commands;
     assert `result.stdout.strip()` equals expected string exactly.
   - any failing case → empty stdout, single stderr line matching
     `^(MathError|SyntaxError|ValueError|ArgumentError): `, exit 1.
   - no stderr output on success (agents often merge streams).
2. **Unit tests per op module** — math correctness, precision rounding, edge
   inputs (empty dataset, single-element matrix, imaginary/complex sympy
   results, negative base conversions).

Representative contract cases:

- `calc eval "2+2"` → `4`
- `calc eval "1/0"` → stderr `MathError: division by zero`, exit 1
- `calc eval "(2+3"` → stderr `SyntaxError: ...`, exit 1
- `calc matrix multiply "[[1,2],[3,4]]" "[[1],[2]]"` → `[[5],[11]]`
- `calc matrix multiply "[[1,2]]" "[[1,2]]"` → `MathError: ...incompatible dimensions`
- `calc matrix inverse "[[1,2],[3,4]]"` → determinant 0 case → MathError
- `calc convert-unit 1 miles km` → `1.6093` (pint float precision — pin it)
- `calc convert-unit 1 furlongs km` → `ValueError: ...`, exit 1
- `calc physics-constant notathing` → `ValueError: ...`, exit 1
- `calc physics kinematics --solve d` (missing vars) → `ArgumentError: ...`
- `calc vector dot "[1,2]" "[1,2,3]"` → MathError (dimension mismatch)

Run under `uv run pytest`; CI-able with plain `uv run pytest` in a
uv-installed env. Golden-file tests NOT used — contract tests assert literal
strings, stronger than goldens.

## 5. Security notes

- `eval` uses simpleeval, which never calls Python `eval`/`exec` internally;
  verify at review time that no code path falls back to raw eval (e.g. for
  chained ops or numeric literals) — a hardcoded test asserts simpleeval usage
  and that `__import__`, `open`, attribute access on dunder names fail as
  SyntaxError.
- Matrix parsing uses `json.loads` only (JSON, not Python literals — `ast` is
  avoided on principle; if JSON is rejected by the agent, error says so).
- No file I/O, no network, no subprocess in any op module.

## 6. Spec gaps raised explicitly

These are underspecified in the requirements doc; decisions proposed here, to
be ratified before implementation:

1. **`convert-base` semantics are thin.** Spec says `int(val, base)` but
   doesn't define: input format per base (e.g. hex `0x`-prefix or bare?),
   negative numbers, fractional values (bases 2/8/16 for floats is
   ill-defined), and output case (`ff` vs `FF`). **Decision:** integer-only,
   bare digit strings parsed via explicit base maps
   (`dec="0123456789", hex="0123456789abcdef"` case-insensitive in, lowercase
   out), negatives supported via sign, fractional input → `MathError` (or a
   separate `convert-base --fractional` flag if ever needed). Raise for owner
   confirmation.
2. **`convert-unit` temperature** works via pint `degC`/`degF` (offset units),
   which is correct — but spec lists `degC` only as an example, not a
   requirement. No action needed; flagging that offset-unit conversion must be
   tested explicitly (a naive multiplicative implementation silently returns
   wrong answers for °C↔°F).
3. **`finance fv/pv/pmt` argument-to-operation mapping is ambiguous.** Spec
   offers `--pv, --fv, --rate, --periods, --principal` but doesn't say which
   combination each operation requires, or what happens with
   mutually-redundant inputs (e.g. `pmt` given both `--pv` and `--principal`).
   **Decision:** mirror numpy-financial's signatures; `pmt` uses
   `--principal` (alias `--pv`), strict "exactly the required set, nothing
   else" validation → `ArgumentError` otherwise. Raise for confirmation.
4. **`physics` domain equation sets are unspecified.** "kinematics, force,
   energy" with `--v0 --t --a --m --f` implies but does not enumerate the
   equations (e.g. is `d = v0*t + ½at²` in? `v = v0 + at`? `F = ma`? `KE =
   ½mv²`? `W = F*d`?). The design will carry an explicit `EQUATIONS` registry
   per domain (documented in README) so the set is reviewable; the registry,
   not sympy heuristics, decides solvability. Needs owner sign-off on the
   list.
5. **`--precision` scope.** Spec gives it to `eval` only. Stat/finance/matrix/
   physics results are floats too. **Decision:** support `--precision`
   globally (default 4) for float-rendering subcommands; harmless
   generalization, consistent output.
6. **`calculus integrate` definite vs indefinite.** Spec makes `--lower/--upper`
   optional, implying symbolic indefinite integral when both are absent. That
   returns an expression, not a number — the render layer must string-ify
   sympy expressions (e.g. `x**3/3`). Confirmed workable; documented, not a
   blocker.
7. **`stat mode` on multimodal data** — numpy `mode` semantics vs stdlib
   `statistics.mode` differ (last-seen vs first-seen multimodal). **Decision:**
   use `statistics.multimode`, join multiple modes comma-separated on stdout —
   but note this violates "single value" purity; alternative is first mode
   only. Raise for owner choice; default = first mode only (cleanest stdout
   contract).
8. **Large/complex results.** sympy can return `oo`, `zoo`, `nan`, or complex
   numbers. Rendering rules for these (stdout as `inf`? `zoo`?) are
   unspecified. **Decision:** `inf`/`-inf`/`nan` via float rendering;
   `zoo`/complex → `MathError` (result not representable as a real number).
9. **Package name collision:** the Python module is `calc`; PyPI has a `calc`
   package. Irrelevant if never published; distribution method (uv tool, PATH
   script, agent-side wrapper) is unspecified in the spec — assuming local
   install only.

## 7. Non-goals

- No interactive mode, no daemon, no config file (defaults are code constants).
- No output formats beyond the plain result (no JSON/CSV output mode — if
  agents need it later, add `--format json` as an additive flag).
- No arbitrary-precision decimals in v1 (float64 throughout except sympy
  exact results); note as future work.