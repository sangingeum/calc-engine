---
name: calc-engine
description: Deterministic `calc` CLI math engine for AI agents — zero-chat stdout, typed stderr errors, 17 subcommands (eval, stat, finance, matrix, convert-base, convert-unit, calculus, physics-constant, physics, vector, bits, endian, hash, crc, base64, datetime, regex). Use whenever an agent needs safe computation offloaded to a subprocess.
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

---

## 1. eval — expression evaluation

Safe evaluation via `simpleeval` (no Python `eval`/`exec`). Standard
arithmetic operators (`+ - * / // % **`), comparison (`< <= > >= == !=`),
and boolean (`and or not`) operators all work.

**Functions — the exhaustive list (30):**

| Category | Functions |
|---|---|
| roots/power | `sqrt`, `cbrt`, `isqrt` (integer sqrt), `pow` |
| trigonometry | `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2` |
| hyperbolic | `sinh`, `cosh`, `tanh` |
| logarithms | `log` (natural; `log(x, base)` two-arg), `log2`, `log10`, `log1p` |
| exponential | `exp`, `expm1` |
| rounding | `floor`, `ceil`, `trunc`, `fabs` |
| combinatorics | `factorial`, `gcd`, `lcm` |
| misc | `hypot`, `degrees`, `radians` |

**Constants — the exhaustive list (3):** `pi`, `tau`, `e`

Anything else (attribute access, `__import__`, `open`) is rejected.

```bash
calc eval "452.12 * (14 / 3.14)"
calc eval "sqrt(2)" --precision 6            # 1.414214
calc eval "atan2(1, 1) * 2"                  # 1.5708
calc eval "factorial(10)"                    # 3628800
```

---

## 2. physics-constant — physical constants

Looks up an attribute name in `scipy.constants` and prints its SI value.
**Exhaustive symbol list (155):**

| Group | Symbols |
|---|---|
| universal | `G` `gravitational_constant` `c` `speed_of_light` `sigma` `Stefan_Boltzmann` `Wien` `Rydberg` `R` `gas_constant` `Boltzmann` `k` (Boltzmann) `h` `Planck` `hbar` `fine_structure` `alpha` `e` `elementary_charge` `epsilon_0` `mu_0` `golden` `golden_ratio` `Avogadro` `N_A` `atm` `atmosphere` `zero_Celsius` `degree_Fahrenheit` `pi` |
| particles/mass | `electron_mass` `m_e` `proton_mass` `m_p` `neutron_mass` `m_n` `atomic_mass` `m_u` `u` |
| energy | `eV` `electron_volt` `calorie` `calorie_IT` `calorie_th` `Btu` `Btu_IT` `Btu_th` `erg` `ton_TNT` |
| length/distance | `angstrom` `astronomical_unit` `au` `fermi` `light_year` `parsec` `micron` `mil` `foot` `inch` `yard` `mile` `nautical_mile` `survey_foot` `survey_mile` `arcminute` `arcmin` `arcsecond` `arcsec` `degree` |
| time | `minute` `hour` `day` `week` `year` `Julian_year` |
| area/volume | `hectare` `acre` `barrel` `bbl` `gallon` `gallon_US` `gallon_imp` `liter` `litre` `fluid_ounce` `fluid_ounce_US` `fluid_ounce_imp` `carat` `point` `pt` |
| mass | `gram` `grain` `ounce` `oz` `pound` `lb` `stone` `slug` `slinch` `long_ton` `short_ton` `metric_ton` `troy_ounce` `troy_pound` |
| force/pressure | `dyn` `dyne` `kgf` `kilogram_force` `pound_force` `lbf` `psi` `torr` `mmHg` `bar` `mach` `hp` `horsepower` |
| speed | `kmh` `knot` `mph` `speed_of_sound` |
| SI prefixes (multipliers) | `quetta` `ronna` `yotta` `zetta` `exa` `peta` `tera` `giga` `mega` `kilo` `hecto` `deka` `deci` `centi` `milli` `micro` `nano` `pico` `femto` `atto` `zepto` `yocto` `ronto` `quecto` and binary: `kibi` `mebi` `gibi` `tebi` `pebi` `exbi` `zebi` `yobi` |

(These are the symbols scipy.constants exposes as numeric scalars; each
yields its SI-magnitude float. Unknown symbols are `ValueError`.)

```bash
calc physics-constant c     # 299792458.0000
calc physics-constant G     # 6.674e-11
```

---

## 3. convert-base — integer base conversion

**Exhaustive semantics:**

- **Bases accepted**: names `bin` (2), `oct` (8), `dec` (10), `hex` (16), or
  **any integer 2–36** for `--from` and `--to`.
- **Input digits** (case-insensitive): `0-9` then `a-z` — digit `v` in base
  *b* requires `v < b` (e.g. `ff` valid for hex, invalid for dec).
- **Output**: lowercase digit string, no prefixes (`0x`-style prefixes are
  NOT accepted on input either — bare digit strings only).
- **Sign**: leading `-` or `+` allowed; negatives round-trip.
- **Integers only**: any `.` in the value is a `MathError`.

```bash
calc convert-base 255 --from dec --to hex   # ff
calc convert-base FF --from hex --to bin    # 11111111
calc convert-base -42 --from dec --to hex   # -2a
calc convert-base 1010 --from bin --to 36   # s
```

---

## 4. convert-unit — unit conversion

Backend is **pint**: every unit name in the pint registry works, including
all SI prefixes (`k`, `M`, `G`, `m`, `µ`/`u`, `n`, `p`, ... and binary
`Ki`, `Mi`, `Gi`, ...). That is **1038 unit names** in the installed
registry — too many to list here; the complete list is enumerable with:

```bash
uv run python -c "import pint; print(' '.join(sorted(pint.UnitRegistry()._units)))"
```

**Exhaustive dimensionality coverage** (any unit of the same dimension
converts to any other; these are the common members of each family):

| Dimension | Units (common members) |
|---|---|
| length | `m` `km` `cm` `mm` `nm` `um`/`µm` `in` `ft` `yd` `mi` `nmi` `ly` `au` `pc` `angstrom` `Å` `fathom` `chain` `rod` `league` |
| mass | `kg` `g` `mg` `ug`/`µg` `t`/`tonne` `lb` `oz` `st` (stone) `ton` `u`/`amu`/`dalton` `grain` `carat` `dwt` (pennyweight) |
| time | `s` `ms` `us`/`µs` `ns` `min` `h`/`hr` `day` `week` `month` `year` `decade` `century` `fortnight` |
| temperature | `degC`/`celsius`/`°C` `degF`/`fahrenheit`/`°F` `K`/`kelvin`/`degK` `degR`/`rankine` `degRe`/`reaumur` — offset units handled correctly |
| speed | `m/s` `mph` `km/h`/`kph` `knot`/`kn` `ft/s`/`fps` `mach` |
| volume | `L`/`l`/`liter` `mL` `m^3`/`m³` `gal` `qt` `pt` `cup` `floz` `tbsp` `tsp` `bbl` `bu` (bushel) `pk` (peck) `gill` `stere` |
| area | `m^2` `ha` `acre` `ft^2` `in^2` `mi^2` `are` `barn` `DPI`-family is length²-compatible |
| pressure | `Pa` `kPa` `MPa` `bar` `mbar` `atm` `psi` `torr` `mmHg` `inHg` `inH2O` `mmH2O` |
| energy | `J` `kJ` `cal` `kcal` `Wh` `kWh` `eV` `Btu` `erg` `ft_lb` `therm` `ton_TNT` `hartree` |
| power | `W` `kW` `MW` `hp` `metric_horsepower` `boiler_horsepower` |
| force | `N` `kN` `lbf` `dyn`/`dyne` `kgf` `kip` `poundal`/`pdl` `pond` |
| angle | `rad` `deg`/`arcdeg` `grad`/`gon` `arcmin` `arcsec` `turn`/`circle` `octant` `quadrant` |
| data | `B`/`byte` `KB` `MB` `GB` `TB` `KiB` `MiB` `GiB` `bit` `kbit` `Mb` `Gb` |
| frequency | `Hz` `kHz` `MHz` `GHz` `rpm`/`rps` `bpm` |
| electric/magnetic | `A` `V` `ohm`/`Ω` `F` `H` (henry) `T` (tesla) `Wb` `gauss` `G` `oersted` `Oe` `weber` `siemens`/`S` `mho` `coulomb`/`C` `Bi` (biot) `statC`/`esu`/`Fr` (franklin) |
| light | `lm` (lumen) `lx` (lux) `cd` (candela) `nit` `lambert` `stilb` |
| radioactivity/medical | `Bq` `Ci` `Gy` `Sv` `rem` `rad` (rad) `kat`/`katal` `U` (enzyme unit) |
| dimensionless | `percent`/`%` `permille`/`‰` `ppm` `ppb` `radian`-free ratios |

Compound unit strings work: `m/s`, `kg/m^3`, `N*m`, `mile/hour`,
`gallon/minute`. Unknown units are `ValueError`; mismatched dimensions are
also `ValueError` (`DimensionalityError`).

```bash
calc convert-unit 1 miles km       # 1.6093
calc convert-unit 100 degC degF    # 212.0000
calc convert-unit 5 gallon minute  # ✗ ValueError — compound needs a slash
calc convert-unit 60 mph m/s       # 26.8224
```

---

## 5. Other subcommands (quick reference)

```bash
calc stat mean "[1,2,3,4]"            # mean|median|mode|stdev|variance|pvariance|sum|min|max|count|geometric_mean|harmonic_mean (JSON array; mode returns FIRST mode)
calc finance fv --rate 0.05 --periods 10 --pv 1000
calc finance pv --rate 0.05 --periods 10 --fv 1628.89
calc finance pmt --rate 0.05 --periods 10 --principal 1000   # pmt: --principal, --pv alias; strict exact arg sets
calc matrix multiply "[[1,2],[3,4]]" "[[1],[2]]"    # multiply|add|subtract|inverse|determinant|transpose (strict JSON)
calc calculus derive "x**2 * sin(x)" --var x
calc calculus integrate "x**2" --var x --lower 0 --upper 1    # definite -> 0.3333; without bounds -> symbolic string
calc calculus limit "1/x" --var x --approach 0
calc physics kinematics --solve d --v0 10 --t 2 --a 3         # registry below
calc vector dot "[1,2,3]" "[4,5,6]"   # dot|cross|norm|add|subtract (strict JSON)
```

### Additional subcommands (quick reference)

```bash
calc bits and 0xF0 0x3C --width 8     # fixed-width integer ops; --width REQUIRED (8|16|32|64)
                                      # and|or|xor|not|shl|shr|sar|rol|ror|popcount|clz|ctz|to-signed|to-unsigned|float-to-bits|bits-to-float
                                      # input: 0x/0b/decimal; output decimal by default, --format hex|bin (lowercase, zero-padded, no prefix); --signed for two's-complement view
calc bits and 0xF0 0x3C --width 8 --format hex   # 30
calc bits float-to-bits 1.0 --width 32           # 3f800000
calc endian swap 0x12345678 --width 32           # 78563412 (swap|to-bytes|from-bytes; --width required for swap/to-bytes)
calc endian to-bytes 0x12345678 --width 32 --order little  # 78563412
calc endian from-bytes 78563412 --order little   # 305419896 (input hex bytes, output decimal)
calc hash sha256 "hello"                # md5|sha1|sha256|sha512|sha3_256|blake2b; input is UTF-8 text
calc hash sha256 68656c6c6f --input hex # raw bytes via hex
calc crc crc32 "123456789"              # cbf43926 (check values are unit tests)
calc crc crc32c "123456789"             # e3069283
calc crc crc16-ccitt-false "123456789"  # 29b1
calc crc crc16-xmodem "123456789"       # 31c3
calc crc crc16-modbus "123456789"       # 4b37
calc crc crc8 "123456789"               # f4
calc base64 encode "hello"              # aGVsbG8=
calc base64 decode "aGVsbG8="           # hello
calc base64 decode "aGVsbG8=" --output hex   # 68656c6c6f (non-UTF-8 bytes)
calc base64 encode "hello?>" --urlsafe  # URL-safe alphabet (-_)
calc datetime from-epoch 1700000000                        # 2023-11-14T22:13:20+00:00
calc datetime from-epoch 1700000000 --tz Asia/Seoul        # 2023-11-15T07:13:20+09:00
calc datetime to-epoch "2023-11-14T22:13:20+00:00"         # 1700000000
calc datetime diff "2024-01-01T00:00:00+00:00" "2024-03-01T00:00:00+00:00" --unit days   # 60.0000 (right - left)
calc datetime add "2024-02-28T12:00:00+00:00" --days 2     # 2024-03-01T12:00:00+00:00
calc datetime weekday "2024-02-29"                         # Thursday
calc datetime convert-tz "2024-03-10T12:00:00" --from America/New_York --to Asia/Seoul   # 2024-03-11T01:00:00+09:00
calc regex test '^\d+$' "12345"                 # true
calc regex findall '\d+' "a1b22c333"            # [1,22,333]
calc regex groups '(\w+)@(\w+)\.com' "x bob@example.com y"   # [bob,example]
calc regex sub '\s+' ' ' "a   b  c"             # a b c
calc regex test 'hello' "HELLO" --flags i       # true (flags: subset of i m s x a)
```

Notes:

- **bits/endian**: omitting `--width` (or an unsupported width) is
  `ArgumentError`; a value that does not fit the width is `MathError`.
  `float-to-bits`/`bits-to-float` require `--width 32|64` (IEEE-754
  binary32/binary64); width 8/16 is an `ArgumentError` (no half-precision
  in v1).
- **datetime**: a naive timestamp (no offset) without `--tz`/`--from` is an
  `ArgumentError`; unknown timezone is `ValueError`; `add` supports only
  days/hours/minutes/seconds/weeks (no month arithmetic).
- **regex**: **Python dialect only; verify separately for other languages.**
  `test` returning false is a normal success (exit 0); invalid pattern is
  `SyntaxError`; matching is guarded by a 2 s subprocess timeout
  (catastrophic backtracking -> `MathError`).

### physics equation registry (v1 — fixed and reviewable)

| Domain | Equations | Symbols |
|---|---|---|
| kinematics | `d = v0*t + a*t^2/2` | `d v0 t a` |
| | `v = v0 + a*t` | `v v0 a t` |
| | `v^2 = v0^2 + 2*a*d` | `v v0 a d` |
| force | `F = m*a` | `F m a` |
| energy | `KE = m*v^2/2` | `KE m v` |
| | `W = F*d` | `W F d` |
| | `PE = m*g*h` | `PE m g h` (`g` optional, default 9.80665) |

Supply the target symbol plus every other symbol of exactly one equation;
unknown or ambiguous targets are `ArgumentError`.

---

## Error handling (self-correction protocol)

On failure, parse the stderr prefix and adjust the call:

| Prefix | Meaning | Typical correction |
|---|---|---|
| `MathError:` | div by zero, bad dimensions, singular inverse, non-real result, fractional base conversion | change the math, not the syntax |
| `SyntaxError:` | unparseable expression, invalid JSON, invalid digit for base | fix quoting/format; matrices are JSON, not Python literals |
| `ValueError:` | unknown unit or physical constant | use a standard unit string (e.g. `degC`) or known symbol |
| `ArgumentError:` | missing/extra args, unknown operation/domain/symbol | provide exactly the required argument set |

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
- `eval` has no variables other than `pi`/`tau`/`e` — no `x` in eval
  (use `calculus` with `--var` for symbolic work).
- `convert-base` is integer-only; fractional input is a `MathError`.
- `stat mode` on multimodal data returns the first mode only.
