---
name: calc-engine
description: Deterministic `calc` CLI math engine for AI agents — zero-chat stdout, typed stderr errors, 10 subcommands (eval, stat, finance, matrix, convert-base, convert-unit, calculus, physics-constant, physics, vector). Use whenever an agent needs safe computation offloaded to a subprocess.
---

# calc — CLI math engine for agents

A deterministic CLI that offloads math from the agent's own reasoning. The
contract is byte-exact:

- **stdout**: ONLY the result (one line; trailing newline). No labels, no prose.
- **stderr** (on failure): exactly one line `ErrorType: description`.
- **exit code**: `0` success, `1` domain failure, `2` bad CLI usage (argparse).

## Invocation

```bash
calc <subcommand> [args] [--precision N]
```

If the `calc` console script is not on PATH, run from the repo via
`uv run calc <subcommand> ...`.

## Subcommands

```bash
calc eval "452.12 * (14 / 3.14)"          # arithmetic; simpleeval, no eval/exec
calc eval "sqrt(2)" --precision 6         # 1.414214
calc stat mean "[1,2,3,4]"                # mean|median|mode|stdev|variance|sum|... (JSON array)
calc finance fv --rate 0.05 --periods 10 --pv 1000     # fv|pv|pmt, strict arg sets
calc finance pmt --rate 0.05 --periods 10 --principal 1000
calc matrix multiply "[[1,2],[3,4]]" "[[1],[2]]"       # multiply|add|subtract|inverse|determinant|transpose (strict JSON)
calc convert-base 255 --from dec --to hex # ff (integer-only; bin|oct|dec|hex or 2-36)
calc convert-unit 1 miles km              # pint-backed; 100 degC degF -> 212.0000
calc calculus derive "x**2 * sin(x)" --var x            # derive|integrate|limit
calc calculus integrate "x**2" --var x --lower 0 --upper 1   # definite -> 0.3333
calc physics-constant G                   # scipy.constants -> 6.674e-11
calc physics kinematics --solve d --v0 10 --t 2 --a 3   # kinematics|force|energy registry
calc vector dot "[1,2,3]" "[4,5,6]"       # dot|cross|norm|add|subtract (strict JSON)
```

## Error handling (self-correction protocol)

On failure, parse the stderr prefix and adjust the call:

| Prefix | Meaning | Typical correction |
|---|---|---|
| `MathError:` | div by zero, bad dimensions, singular inverse, non-real result | change the math, not the syntax |
| `SyntaxError:` | unparseable expression, invalid JSON | fix quoting/format; matrices are JSON, not Python literals |
| `ValueError:` | unknown unit or physical constant | use a standard unit string (e.g. `degC`) or known symbol |
| `ArgumentError:` | missing/extra args, unknown operation or symbol | provide exactly the required argument set |

Always treat non-zero exit as failure; never depend on stderr when exit is 0
(stderr is empty on success).

## Rendering

`--precision N` (default 4) applies to float output on every subcommand.
Fixed-point within magnitude band [1e-4, 1e16); general format (significant
digits) outside it. `inf`/`-inf`/`nan` render literally; complex results are
`MathError`. Symbolic calculus results (indefinite integrate, limits at
infinity) return sympy-style strings, e.g. `x**3/3`.

## Notes for agent callers

- Pass matrices/vectors/datasets as **strict JSON** strings; quote them.
- `convert-base` is integer-only; fractional input is a `MathError`.
- `physics` solvability is registry-decided: supply the target symbol plus
  every other symbol of exactly one equation (energy: `g` optional, defaults
  9.80665).
- `stat mode` on multimodal data returns the first mode only.
