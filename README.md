# calc-engine

`calc` is a deterministic, subcommand-driven CLI math engine designed for AI
agents. The contract with the calling agent is byte-exact:

- **stdout** carries ONLY the result — a number or a string, no labels, no
  banners, no commentary. A trailing newline is the only decoration.
- **stderr** on failure carries exactly one line of the form
  `ErrorType: description`.
- **exit code** is `0` on success and non-zero (`1`) on any domain failure.
  Invalid command-line usage exits `2` with argparse usage text on stderr.

## Installation

This is a `uv`-managed Python package:

```bash
uv sync                    # create .venv and install dependencies
uv run calc eval "2+2"     # run via uv
# or install the console script into the environment:
uv tool install --editable .
```

## Subcommands

### eval — expression evaluation

```bash
calc eval "2+2"                     # 4
calc eval "sqrt(2)" --precision 6   # 1.414214
```

Safe evaluation via `simpleeval` (no Python `eval`/`exec`). Supported
functions include `sqrt, sin, cos, tan, log, log2, log10, exp, floor, ceil,
fabs, factorial, gcd, lcm, hypot, pow, ...`; constants `pi`, `tau`, `e`.

### stat — statistics

```bash
calc stat mean "[1,2,3,4]"          # 2.5000
calc stat mode "[1,2,2,3]"          # 2
```

Operations: `mean, median, mode, stdev, variance, pvariance, sum, min, max,
count, geometric_mean, harmonic_mean`. Dataset is a JSON array of numbers.
On multimodal data, `mode` returns the FIRST mode only (single-value stdout
contract).

### finance — financial operations

Mirrors numpy-financial signatures with strict exactly-required-set
validation — providing anything other than the exact required set is an
`ArgumentError`.

```bash
calc finance fv  --rate 0.05 --periods 10 --pv 1000
calc finance pv  --rate 0.05 --periods 10 --fv 1628.89
calc finance pmt --rate 0.05 --periods 10 --principal 1000
# pmt also accepts --pv as an alias of --principal (both given -> ArgumentError)
```

### matrix — matrix operations (JSON)

```bash
calc matrix multiply "[[1,2],[3,4]]" "[[1],[2]]"   # [[5],[11]]
calc matrix determinant "[[1,2],[3,4]]"            # -2.0000
calc matrix inverse "[[4,7],[2,6]]"
calc matrix transpose "[[1,2],[3,4]]"              # [[1,3],[2,4]]
```

Operations: `multiply, add, subtract, inverse, determinant, transpose`.
Matrices are strict JSON (arrays of arrays of numbers).

### convert-base — integer base conversion

Integer-only, bare digit strings, case-insensitive input, lowercase output,
negatives via leading sign. Fractional input is a `MathError`. Bases:
`bin|oct|dec|hex` or any integer 2–36.

```bash
calc convert-base 255 --from dec --to hex   # ff
calc convert-base FF --from hex --to bin    # 11111111
calc convert-base -42 --from dec --to hex   # -2a
```

### convert-unit — unit conversion

```bash
calc convert-unit 1 miles km    # 1.6093
calc convert-unit 100 degC degF # 212.0000  (offset units handled correctly)
```

### calculus — derive / integrate / limit (sympy)

```bash
calc calculus derive "x**2" --var x                          # 2*x
calc calculus integrate "x**2" --var x                       # x**3/3  (symbolic)
calc calculus integrate "x**2" --var x --lower 0 --upper 1   # 0.3333
calc calculus limit "1/x" --var x --approach 0               # inf (see below)
```

### physics-constant — physical constants

```bash
calc physics-constant c     # 299792458.0000  (speed of light, m/s)
calc physics-constant G     # 6.674e-11
```

Constants come from `scipy.constants`; unknown symbols are a `ValueError`.

### physics — solve a domain equation

```bash
calc physics kinematics --solve d --v0 10 --t 2 --a 3   # 26.0000
calc physics force --solve F --m 5 --a 2                # 10.0000
calc physics energy --solve PE --m 2 --h 5              # 98.0665
```

The equation registry (v1 — fixed and reviewable):

| Domain | Equations |
|---|---|
| kinematics | `d = v0*t + a*t^2/2`, `v = v0 + a*t`, `v^2 = v0^2 + 2*a*d` |
| force | `F = m*a` |
| energy | `KE = m*v^2/2`, `W = F*d`, `PE = m*g*h` (`g` optional, default `9.80665`) |

Solvability is decided by the registry: the target symbol plus every other
symbol of exactly one equation must be provided; unknown or ambiguous
targets are `ArgumentError`.

### vector — vector operations (JSON)

```bash
calc vector dot "[1,2,3]" "[4,5,6]"   # 32.0000
calc vector cross "[1,0,0]" "[0,1,0]" # [0,0,1]
calc vector norm "[3,4]"              # 5.0000
```

Operations: `dot, cross, norm, add, subtract`. Vectors are strict JSON
arrays of numbers.

### bits — fixed-width integer operations

`--width` is **required** (8|16|32|64); omitting it is an `ArgumentError`.
Integers accept `0x`, `0b`, and decimal (with sign); a value that does not
fit the width is a `MathError`. Default output is decimal; `--format hex|bin`
renders lowercase, zero-padded, no prefix. `--signed` interprets results as
two's complement.

```bash
calc bits and 0xF0 0x3C --width 8                # 48
calc bits not 0x0F --width 8                     # 240
calc bits sar -128 1 --width 8 --signed          # -64
calc bits rol 0x81 1 --width 8                   # 3
calc bits popcount 255 --width 8                 # 8
calc bits clz 1 --width 32                       # 31
calc bits to-signed 0xFF --width 8               # -1
calc bits float-to-bits 1.0 --width 32           # 3f800000
calc bits bits-to-float 0x3fc00000 --width 32    # 1.5000
calc bits and 0xF0 0x3C --width 8 --format hex   # 30
```

Operations: `and or xor not shl shr sar rol ror popcount clz ctz
to-signed to-unsigned float-to-bits bits-to-float`.

`float-to-bits` / `bits-to-float` require `--width 32` or `--width 64`
(IEEE-754 binary32/binary64); other widths are an `ArgumentError`.

### endian — byte-order conversions

Separate from `bits` by design: endianness converts between values and byte
sequences. `swap`/`to-bytes` output lowercase hex; `from-bytes` takes a hex
byte string and outputs decimal.

```bash
calc endian swap 0x12345678 --width 32                    # 78563412
calc endian to-bytes 0x12345678 --width 32 --order little # 78563412
calc endian from-bytes 78563412 --order little            # 305419896
```

### hash — digests

Default input is UTF-8 text; `--input hex` treats it as raw bytes.

```bash
calc hash sha256 hello              # 2cf24dba5fb0...b9824
calc hash md5 hello                 # 5d41402abc4b2a76b9719d911017c592
calc hash sha256 68656c6c6f --input hex
```

Algorithms: `md5, sha1, sha256, sha512, sha3_256, blake2b`.

### crc — CRC digests (fixed variant registry)

```bash
calc crc crc32 "123456789"              # cbf43926
calc crc crc32c "123456789"             # e3069283
calc crc crc16-ccitt-false "123456789"  # 29b1
calc crc crc16-xmodem "123456789"       # 31c3
calc crc crc16-modbus "123456789"       # 4b37
calc crc crc8 "123456789"               # f4
```

Variants: `crc32, crc32c, crc16-ccitt-false, crc16-xmodem, crc16-modbus, crc8`
(parameters fixed by name; `--input hex` supported like `hash`).

### base64 — encode/decode

```bash
calc base64 encode "hello"              # aGVsbG8=
calc base64 decode "aGVsbG8="           # hello
calc base64 decode "aGVsbG8=" --output hex   # 68656c6c6f (for non-UTF-8 bytes)
calc base64 encode "hello?>" --urlsafe  # URL-safe alphabet (-_)
```

### datetime — date/time operations

The reference time is always passed in as an argument (no `now`). Output is
ISO-8601 with explicit offset. **Naive timestamps are an `ArgumentError`**
unless `--tz`/`--from` supplies the zone; unknown timezones are a
`ValueError`. `add` supports only `--days --hours --minutes --seconds --weeks`
(month arithmetic is deliberately absent — "Jan 31 + 1 month" is ambiguous).

```bash
calc datetime from-epoch 1700000000                       # 2023-11-14T22:13:20+00:00
calc datetime from-epoch 1700000000 --tz Asia/Seoul       # 2023-11-15T07:13:20+09:00
calc datetime to-epoch "2023-11-14T22:13:20+00:00"        # 1700000000
calc datetime diff "2024-01-01T00:00:00+00:00" "2024-03-01T00:00:00+00:00" --unit days
                                                          # 60.0000 (right - left)
calc datetime add "2024-02-28T12:00:00+00:00" --days 2    # 2024-03-01T12:00:00+00:00
calc datetime weekday "2024-02-29"                        # Thursday
calc datetime convert-tz "2024-03-10T12:00:00" --from America/New_York --to Asia/Seoul
                                                          # 2024-03-11T01:00:00+09:00
```

### regex — pattern operations (Python dialect only)

Python `re` dialect only in v1 (`--flavor python`); verify patterns
separately for other languages. Matching runs in a subprocess with a 2 s
execution budget — catastrophic backtracking is a `MathError`, not a hang.
`test` returning false is a normal success (exit 0); only an invalid pattern
is a `SyntaxError`. Flag letters: `i m s x a`.

```bash
calc regex test '^\d+$' "12345"               # true
calc regex test 'hello' "HELLO" --flags i     # true
calc regex findall '\d+' "a1b22c333"          # [1,22,333]
calc regex groups '(\w+)@(\w+)\.com' "x bob@example.com y"   # [bob,example]
calc regex sub '\s+' ' ' "a   b  c"           # a b c
```

## Global options

`--precision N` (default `4`) applies to float rendering on every
subcommand. Within the magnitude band [1e-4, 1e16) (and for exact zero) it
controls decimal places (fixed-point); outside the band it controls
significant digits via general format (e.g. `calc physics-constant G` →
`6.674e-11`). `inf`, `-inf`, and `nan` render literally; complex or
non-real results are a `MathError`.

## Error taxonomy

| stderr prefix | Meaning |
|---|---|
| `MathError` | invalid math: division by zero, bad dimensions, singular inverse, non-real result |
| `SyntaxError` | bad input formatting: unparseable expression, invalid JSON, invalid digits |
| `ValueError` | unsupported unit or unknown physical constant |
| `ArgumentError` | missing/extra arguments, unknown operation/algorithm/CRC variant/symbol, naive timestamp without --tz/--from, missing --width |
| `MathError` | invalid math: division by zero, bad dimensions, singular inverse, non-real result, value does not fit the bit width, negative shift, regex execution budget exceeded |

## Agent integration contract

An agent should invoke `calc <subcommand> [args]` and:

1. read stdout as the result (exactly one line; parse it as a number unless
   the subcommand documents string output);
2. treat a non-zero exit code as failure and read the single stderr line for
   `ErrorType: description`;
3. not depend on any stderr output when the exit code is 0 (stderr is empty
   on success);
4. pass `--precision` when more/fewer decimal places are needed.

## Security notes

- Expression evaluation uses `simpleeval` — Python `eval`/`exec` are never
  invoked; dunder attribute access, `__import__`, and `open` fail.
- Matrix/vector parsing is strict JSON (`json.loads`), never Python literals.
- No file I/O, no network, no subprocesses in the computation modules.
  (Exception: `regex` runs its match in a short-lived subprocess as a
  catastrophic-backtracking guard — no untrusted code execution either way.)
