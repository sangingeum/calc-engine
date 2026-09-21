---
name: calc-engine
description: Deterministic `calc` CLI math engine for AI agents — zero-chat stdout, typed stderr errors, 21 subcommands (eval, stat, finance, matrix, convert-base, convert-unit, calculus, physics-constant, physics, vector, bits, endian, hash, crc, base64, datetime, regex, distribution, assert, gof, sym). Use whenever an agent needs safe computation or statistical/probabilistic verification offloaded to a subprocess.
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

**Functions — the exhaustive list (40):**

| Category | Functions |
|---|---|
| roots/power | `sqrt`, `cbrt`, `isqrt` (integer sqrt), `pow` |
| trigonometry | `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `atan2` |
| hyperbolic | `sinh`, `cosh`, `tanh` |
| logarithms | `log` (natural; `log(x, base)` two-arg), `log2`, `log10`, `log1p` |
| exponential | `exp`, `expm1` |
| rounding | `floor`, `ceil`, `trunc`, `fabs`, `round` (banker's rounding) |
| combinatorics | `factorial`, `gcd`, `lcm`, `comb`, `perm` |
| special | `erf`, `erfc`, `gamma`, `lgamma` |
| misc | `hypot`, `degrees`, `radians`, `abs`, `min`, `max` |

**Constants — the exhaustive list (3):** `pi`, `tau`, `e`

Anything else (attribute access, `__import__`, `open`) is rejected.

```bash
calc eval "452.12 * (14 / 3.14)"
calc eval "sqrt(2)" --precision 6            # 1.414214
calc eval "atan2(1, 1) * 2"                  # 1.5708
calc eval "factorial(10)"                    # 3628800
calc eval "erf(1)" --precision 6             # 0.842701
calc eval "gamma(5)"                         # 24
calc eval "comb(5,2)"                        # 10
```

**Variables with `--let`** (repeatable): `calc eval "a*b" --let a=2 --let b=3`
→ `6`. Numeric literals only; names must be valid identifiers and must not
shadow functions/constants (`--let sqrt=2` is an `ArgumentError`).

**Exact rational arithmetic `--exact`**: evaluates with `fractions.Fraction`
(decimal literals parsed exactly) and prints an integer or `p/q` in lowest
terms: `calc eval "-0.35*(1+0.5*(0.5-0.25)*2)" --exact` → `-7/16`. Allowed:
`+ - * / // % **`, integer-valued exponents only, parentheses, numeric
literals. Functions/names are not allowed; anything not exactly representable
is a `MathError: result not exactly representable`. `--exact` with
`--precision` is an `ArgumentError`.

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
calc stat covariance "[1,2,3]" "[2,4,6]"      # 1.3333 — population cov (ddof=0 default); --ddof 1 for sample
calc stat pearson "[1,2,3]" "[2,4,6]"         # 1.0000 — Pearson r; zero variance -> MathError
calc stat spearman "[1,2,3]" "[30,10,20]"     # -0.5000 — average ranks for ties
calc stat rank "[30,10,20]"                   # [3.0000,1.0000,2.0000] — 1-based average ranks
calc stat skewness "[1,2,3,4,10]"             # 1.1384 — population (biased) standardized moment
calc stat kurtosis "[1,2,3,4,10]"             # 2.7880 — population, NON-excess (normal = 3)
calc stat excess-kurtosis "[1,2,3,4,10]"      # -0.2120
calc stat spearman "[1,2,3,4,5,6,7,8]" "[2,1,4,3,6,5,8,7]" --field p   # 0.0020
#   pearson/spearman --field: coefficient|p|t|df|n; --alternative two-sided|greater|less
#   p-value method (pinned): t = r*sqrt((n-2)/(1-r^2)), df = n-2; Spearman =
#   average-rank Pearson with the same t-approximation (scipy convention).
#   |r| = 1 => p = 0; n < 3 => MathError. These are population moments.
calc stat critical-r --n 240 --alpha 0.05     # 0.1267 — smallest |r| significant at alpha
#   r_crit = t_crit/sqrt(n-2+t_crit^2); two-sided uses the 1-alpha/2 t quantile.
calc stat regression "[0,1,2,3]" "[1,3,5,7]" --field slope   # 2.0000
#   --field: slope|intercept|r2|stderr|slope_stderr|residual_stderr|residual_variance
#   stderr IS slope_stderr (explicit alias); residual_stderr = sqrt(SSR/(n-2)); residual_variance = SSR/(n-2)
calc stat quantile "[1,2,3,4,5]" 0.5          # 3.0000 — NumPy 'linear': h=(n-1)*q
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

## distribution — probability distributions (verification backend)

Eleven families; parameters are always **named flags** (abbreviations are
disabled on this subcommand — exact flags only):

| family | flags | parameterization / constraints |
|---|---|---|
| `uniform` | `--low --high` | pdf = 1/(high−low) on [low, high]; low < high |
| `beta` | `--alpha --beta` | shape/shape; both > 0 |
| `normal` | `--mu --sigma` | N(mu, sigma^2); sigma > 0 |
| `lognormal` | `--mu --sigma` | log X ~ N(mu, sigma^2); sigma > 0 |
| `exponential` | `--scale` | rate = 1/scale; scale > 0 |
| `gamma` | `--shape --scale` | both > 0 |
| `binomial` | `--n --p` | n non-negative INTEGER, 0 ≤ p ≤ 1 |
| `poisson` | `--lam` | lam > 0 |
| `t` | `--df` | Student's t (standard); df > 0 |
| `chi2` | `--df` | df > 0 |
| `kumaraswamy` | `--a --b` | a > 0, b > 0; closed-form CDF/PPF; sample via inverse-CDF on the PCG64 uniform stream |

Moments that do not exist (t mean for df ≤ 1) are `MathError: moment
undefined`; moments that are infinite by definition (t variance for
1 < df ≤ 2) render `inf` — never `nan`.

Operations (one value per stdout line, byte-exact):

```bash
calc distribution mean beta --alpha 2 --beta 2           # 0.5000
calc distribution variance beta --alpha 2 --beta 2       # 0.0500
calc distribution variance beta --alpha 4.05 --beta 4.05 # 0.0275  ← named regression case; NOT 0.05
calc distribution stddev beta --alpha 2 --beta 2         # 0.2236
calc distribution skewness beta --alpha 2 --beta 2       # 0.0000
calc distribution kurtosis normal --mu 0 --sigma 1       # 3.0000
calc distribution excess-kurtosis normal --mu 0 --sigma 1 # 0.0000
calc distribution pdf beta 0.5 --alpha 2 --beta 2        # 1.5000 (positional x; --x also accepted)
calc distribution cdf beta 0.5 --alpha 2 --beta 2        # 0.5000
calc distribution ppf beta 0.5 --alpha 2 --beta 2        # 0.5000 (positional q; --q also accepted)
calc distribution validate beta --alpha 2 --beta 2       # true
calc distribution sample beta --alpha 2 --beta 2 --size 5 --seed 123
                                                         # [0.1486,0.7646,0.4182,0.5289,0.7776]
calc distribution compare-moments beta --alpha 2 --beta 2 uniform --low 0 --high 1 --moment mean
                                                         # true
```

Definitions and conventions (pinned by tests):

- **kurtosis** = fourth standardized moment, NON-excess (normal = 3);
  `excess-kurtosis` = kurtosis − 3.
- **sample determinism**: numpy PCG64 (`np.random.default_rng(seed)`,
  numpy 1.26.4 / scipy 1.17.1 pinned in `uv.lock`). `--seed` is REQUIRED; no
  implicit time source; the same seed reproduces the same stream across runs
  and environments. It is NOT expected to match another language/runtime's RNG
  stream — it is for "does theory predict this?" checks, not bit-exact replay.
- **sf**: survival function P(X > x) computed via the library's survival
  function (NOT `1 − cdf`) so extreme tail probabilities keep precision:
  `calc distribution sf normal 8 --mu 0 --sigma 1` → `6.221e-16`.
- **validate** prints `true` on valid parameters; invalid parameters fail
  with a typed `MathError` (e.g. `uniform requires low < high`). Missing
  required parameters are `ArgumentError`.
- **compare-moments** prints `true`/`false` comparing ONE moment
  (`--moment` = mean|variance|stddev|skewness|kurtosis) of two families.
- **describe** is deliberately rejected (it would emit structured output);
  call `mean`/`variance`/`stddev` individually instead.
- `ppf` requires q ∈ [0,1] (else `MathError`); `ppf(0)` on continuous
  families renders `-inf`.
- `cdf(ppf(p)) ≈ p` holds for representative probabilities (tested roundtrip).
- **fit**: closed-form moment matching, `calc distribution fit <family>
  --mean M --variance V --field <param>` (one fitted parameter per call).
  Supported families: `beta` (c = M(1−M)/V − 1; alpha = M·c, beta = (1−M)·c;
  requires 0<M<1, 0<V<M(1−M)), `gamma` (shape = M²/V, scale = V/M),
  `normal` (mu = M, sigma = √V), `lognormal` (sigma² = ln(1+V/M²),
  mu = ln M − sigma²/2), `uniform` (M ∓ √(3V)). Infeasible targets are
  `MathError`; `kumaraswamy` and other families are `ArgumentError`.
```

## gof — goodness-of-fit tests (verification backend)

`--field` is REQUIRED for every op (omitting it is an `ArgumentError`):
`statistic` or `p` (all ops), plus `df` for `chi2`/`chi2-bins`.

```bash
calc gof ks DATA FAMILY [family flags] --field statistic|p
calc gof chi2 OBSERVED EXPECTED [--ddof N] --field statistic|p|df
calc gof chi2-bins DATA FAMILY [family flags] --bins K [--ddof N] --field statistic|p|df
```

- **ks**: one-sample two-sided Kolmogorov–Smirnov test against the family's
  CDF, identical to `scipy.stats.kstest(data, cdf, method='auto')` (pinned
  convention). Continuous families only (`uniform beta normal lognormal
  exponential gamma t chi2 kumaraswamy`); `binomial`/`poisson` are
  `ArgumentError`.
- **chi2**: OBSERVED/EXPECTED are JSON arrays of counts of equal length; sums
  must match (else `MathError`); `df = k − 1 − ddof`.
- **chi2-bins**: K equiprobable bins from the family's PPF at i/K; expected
  count n/K per bin; data outside the family's support ⇒ `MathError` (no
  silent clipping); requires n/K ≥ 5 else `MathError: expected count per bin
  < 5`; `df = K − 1 − ddof`.
- DATA/OBSERVED/EXPECTED accept `@file` / `@-` (see Input resolver).

```bash
calc gof ks "[0.05,0.2,0.35,0.5,0.65,0.8,0.95]" uniform --low 0 --high 1 --field statistic
                                             # 0.0929
calc gof chi2 "[18,22,20,20]" "[20,20,20,20]" --field p   # 0.9402
```

## sym — symbolic equivalence / simplify / expand (real domain)

Symbols must be declared with `--var` (undeclared ⇒ `SyntaxError`). Decimal
literals are parsed as EXACT rationals (0.35 → 7/20) so identities with
decimal coefficients hold exactly.

- `sym equiv EXPR1 EXPR2 --var A ...` prints `true` iff simplify(E1−E2) = 0;
  `false` iff provably non-zero (non-zero constant, or differs by > 1e-9 at
  any point of the fixed rational test grid {1/2, −1/3, 7/5, 3, −2, 11/13,
  1/100}); otherwise `MathError: undecided`. No randomness.
- `sym simplify EXPR` / `sym expand EXPR` print the sympy-style string.

```bash
calc sym equiv "-0.35*(1+0.5*(0.5-A)*2)" "-0.525+0.35*A" --var A   # true
calc sym equiv "(x+1)**2" "x**2+1" --var x                          # false
calc sym expand "(x+1)**2" --var x                                  # x**2 + 2*x + 1
```

## Input resolver: `@file`, `@-`, `@@escape` (applies to data positionals)

Every positional that carries data or text accepts:

| token | meaning |
|---|---|
| `@<path>` | read the file at `<path>` |
| `@-` | read all of stdin |
| `@@<text>` | literal text `@<text>` (escape) |

Applies to: JSON dataset arguments of `stat`, `matrix`, `vector`, `gof`, and
`sym` expressions; text arguments of `regex`; data argument of `hash`, `crc`,
`base64` (read as RAW bytes — no decoding, no newline stripping; `base64
decode` re-encodes as text). Read-only; regular files only; default cap
16 MiB, override with `--max-input-bytes N`. Only one `@-` per invocation.
`--input hex` combined with `@file`: **the `@file` raw bytes take precedence**
(the file's bytes are hashed as-is, not parsed as hex).

```bash
printf '[1,2,3,4]' | calc stat mean @-      # 2.5000
calc hash sha256 @fixture.bin               # digest of the file's bytes
calc hash sha256 @@hello                    # digest of the literal '@hello'
```

Arguments beginning with `-` (e.g. `calc eval "-2+5"`) work everywhere; the
`--` separator also still works.

> **Warning: a distribution's mean matching another distribution does not
> imply variance, tail behavior, modality, or other shape properties are
> matched.** Beta(2,2) and Uniform(0,1) share mean 0.5 but have variances
> 0.05 vs 1/12; Beta(4.05,4.05) has variance ≈ 0.02747252747, NOT 0.05.
> Always verify shape moments separately via `compare-moments`.

## assert — deterministic assertions

```bash
calc assert approx 0.5 0.4999999            # true — |a−e| ≤ atol + rtol·|e|; atol=rtol=1e-6 default
calc assert approx 1 1.000001 --atol 1e-5   # true
calc assert equal 1 1                       # true
calc assert between 0.5 0 1                 # true — endpoints INCLUSIVE
calc assert sign 0.35 positive              # true
calc assert sign 0 zero                     # true
calc assert abs-lt 0.01 0.05                # true — |a| < |b|
calc assert abs-gt 0.10 0.05                # true — |a| > |b|
```

Sign names (exhaustive): `positive, negative, zero, nonnegative, nonpositive`.

Failure is a domain failure: stdout stays empty, stderr is exactly one
`AssertionError: description` line, exit code 1. Malformed calls (unknown
sign, wrong operand count, `low > high` in between) are `ArgumentError`.

---

## Error handling (self-correction protocol)

On failure, parse the stderr prefix and adjust the call:

| Prefix | Meaning | Typical correction |
|---|---|---|
| `MathError:` | div by zero, bad dimensions, singular inverse, non-real result, fractional base conversion | change the math, not the syntax |
| `SyntaxError:` | unparseable expression, invalid JSON, invalid digit for base | fix quoting/format; matrices are JSON, not Python literals |
| `ValueError:` | unknown unit or physical constant | use a standard unit string (e.g. `degC`) or known symbol |
| `ArgumentError:` | missing/extra args, unknown operation/domain/symbol | provide exactly the required argument set |
| `AssertionError:` | failed `assert` operation | the asserted claim is false; not a usage error |

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
