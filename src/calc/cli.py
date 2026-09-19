"""Entry point: parse args, dispatch to a pure handler, render to stdout.

Contract (DESIGN.md 1):
- stdout: ONLY the rendered result (this module is the sole writer);
- stderr: on failure, exactly one line ``<Prefix>: description``;
- exit code: 0 on success, 1 on any domain failure (argparse usage errors
  exit 2 with usage text, documented in the README).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from calc.errors import ArgumentError, CalcError
from calc.ops import (
    base_ops,
    bits_ops,
    calculus_ops,
    datetime_ops,
    eval_ops,
    finance_ops,
    hash_ops,
    matrix_ops,
    physics_ops,
    regex_ops,
    stat_ops,
    unit_ops,
    vector_ops,
)
from calc.render import render


def _build_parser() -> argparse.ArgumentParser:
    precision_parent = argparse.ArgumentParser(add_help=False)
    precision_parent.add_argument(
        "--precision",
        type=int,
        default=4,
        help="decimal places for float output (default: 4)",
    )

    parser = argparse.ArgumentParser(
        prog="calc",
        description="Deterministic, subcommand-driven CLI math engine for agents.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    p = sub.add_parser("eval", parents=[precision_parent], help="evaluate a math expression")
    p.add_argument("expr", help="expression, e.g. '2+2' or 'sqrt(2)'")

    p = sub.add_parser(
        "stat", parents=[precision_parent], help="statistics over a JSON dataset"
    )
    p.add_argument(
        "op",
        help=(
            "mean|median|mode|stdev|variance|pvariance|sum|min|max|count"
            "|geometric_mean|harmonic_mean"
        ),
    )
    p.add_argument("dataset", help="JSON array of numbers, e.g. '[1,2,3]'")

    p = sub.add_parser(
        "finance",
        parents=[precision_parent],
        help="financial operations (numpy-financial)",
    )
    p.add_argument("op", help="fv|pv|pmt")
    p.add_argument("--rate", type=float, default=None, help="interest rate per period")
    p.add_argument("--periods", type=float, default=None, help="number of periods")
    p.add_argument(
        "--pv",
        type=float,
        default=None,
        help="present value (pmt: alias of --principal)",
    )
    p.add_argument("--fv", type=float, default=None, help="future value")
    p.add_argument("--principal", type=float, default=None, help="principal (pmt)")

    p = sub.add_parser(
        "matrix", parents=[precision_parent], help="matrix operations (JSON matrices)"
    )
    p.add_argument("op", help="multiply|add|subtract|inverse|determinant|transpose")
    p.add_argument("matrices", nargs="+", help="one or two JSON matrices")

    p = sub.add_parser(
        "convert-base",
        parents=[precision_parent],
        help="integer base conversion (bare digit strings)",
    )
    p.add_argument("value", help="bare digit string, optional leading sign")
    p.add_argument(
        "--from",
        dest="from_base",
        required=True,
        help="source base: bin|oct|dec|hex|2..36",
    )
    p.add_argument(
        "--to", dest="to_base", required=True, help="target base: bin|oct|dec|hex|2..36"
    )

    p = sub.add_parser(
        "convert-unit", parents=[precision_parent], help="unit conversion via pint"
    )
    p.add_argument("value", type=float, help="numeric value")
    p.add_argument("src", help="source unit, e.g. miles, degC")
    p.add_argument("dst", help="target unit, e.g. km, degF")

    p = sub.add_parser(
        "calculus", parents=[precision_parent], help="derive|integrate|limit via sympy"
    )
    p.add_argument("op", help="derive|integrate|limit")
    p.add_argument("expr", help="expression in the variable, e.g. 'x**2'")
    p.add_argument("--var", required=True, help="variable name")
    p.add_argument("--lower", type=float, default=None, help="lower bound (definite integrate)")
    p.add_argument("--upper", type=float, default=None, help="upper bound (definite integrate)")
    p.add_argument("--approach", type=float, default=None, help="limit point")

    p = sub.add_parser(
        "physics-constant",
        parents=[precision_parent],
        help="physical constant from scipy.constants",
    )
    p.add_argument("symbol", help="constant attribute name, e.g. c, g, G")

    p = sub.add_parser("physics", help="solve a domain equation for a symbol")
    p.add_argument("domain", help="kinematics|force|energy")
    p.add_argument("--solve", required=True, help="symbol to solve for, e.g. d")
    p.add_argument("--precision", type=int, default=4, help=argparse.SUPPRESS)
    p.add_argument("symbols", nargs="*", help=argparse.SUPPRESS)

    p = sub.add_parser(
        "vector", parents=[precision_parent], help="vector operations (JSON vectors)"
    )
    p.add_argument("op", help="dot|cross|norm|add|subtract")
    p.add_argument("vectors", nargs="+", help="one or two JSON vectors")

    p = sub.add_parser(
        "bits", parents=[precision_parent], help="fixed-width integer operations"
    )
    p.add_argument(
        "op",
        help="and|or|xor|not|shl|shr|sar|rol|ror|popcount|clz|ctz|to-signed|to-unsigned|float-to-bits|bits-to-float",
    )
    p.add_argument(
        "values", nargs="+", help="integer literals: 0x/0b/decimal (float for float-to-bits)"
    )
    p.add_argument("--width", type=int, default=None, help="bit width: 8|16|32|64 (required)")
    p.add_argument("--format", default=None, help="output format: hex|bin (default decimal)")
    p.add_argument(
        "--signed", action="store_true", help="interpret results as signed two's complement"
    )

    p = sub.add_parser("endian", parents=[precision_parent], help="byte-order conversions")
    p.add_argument("op", help="swap|to-bytes|from-bytes")
    p.add_argument(
        "value", help="integer literal (swap/to-bytes) or hex byte string (from-bytes)"
    )
    p.add_argument("--width", type=int, default=None, help="bit width: 8|16|32|64 (required)")
    p.add_argument(
        "--order", default=None, help="byte order for to-bytes/from-bytes: little|big"
    )

    p = sub.add_parser("hash", parents=[precision_parent], help="hash digests")
    p.add_argument("algorithm", help="md5|sha1|sha256|sha512|sha3_256|blake2b")
    p.add_argument("data", help="input text (or hex bytes with --input hex)")
    p.add_argument("--input", default=None, help="input format: text|hex (default text)")

    p = sub.add_parser("crc", parents=[precision_parent], help="CRC digests")
    p.add_argument(
        "variant", help="crc32|crc32c|crc16-ccitt-false|crc16-xmodem|crc16-modbus|crc8"
    )
    p.add_argument("data", help="input text (or hex bytes with --input hex)")
    p.add_argument("--input", default=None, help="input format: text|hex (default text)")

    p = sub.add_parser("base64", parents=[precision_parent], help="base64 encode/decode")
    p.add_argument("op", help="encode|decode")
    p.add_argument("data", help="text to encode, or base64 to decode")
    p.add_argument("--urlsafe", action="store_true", help="use the URL-safe alphabet (-_)")
    p.add_argument("--output", default=None, help="decode output format: hex (default UTF-8)")

    p = sub.add_parser(
        "datetime",
        parents=[precision_parent],
        help="date/time operations (reference time always passed in)",
    )
    p.add_argument("op", help="from-epoch|to-epoch|diff|add|weekday|convert-tz")
    p.add_argument("timestamps", nargs="+", help="epoch seconds, ISO-8601 timestamp, or date")
    p.add_argument("--tz", default=None, help="display/source timezone, e.g. Asia/Seoul")
    p.add_argument(
        "--from",
        dest="from_tz",
        default=None,
        help="source timezone for convert-tz (naive input)",
    )
    p.add_argument("--to", dest="to_tz", default=None, help="target timezone for convert-tz")
    p.add_argument("--unit", default=None, help="diff unit: seconds|minutes|hours|days")
    p.add_argument("--days", type=float, default=0.0, help="add: days")
    p.add_argument("--hours", type=float, default=0.0, help="add: hours")
    p.add_argument("--minutes", type=float, default=0.0, help="add: minutes")
    p.add_argument("--seconds", type=float, default=0.0, help="add: seconds")
    p.add_argument("--weeks", type=float, default=0.0, help="add: weeks")

    p = sub.add_parser(
        "regex", parents=[precision_parent], help="regex operations (Python dialect only)"
    )
    p.add_argument("op", help="test|findall|groups|sub")
    p.add_argument(
        "tokens", nargs="+", help="pattern + subject (sub: pattern + replacement + subject)"
    )
    p.add_argument("--flags", default=None, help="flag letters, subset of i m s x a")
    p.add_argument("--flavor", default=None, help="regex flavor (v1: python only)")

    return parser


def _parse_dynamic_kwargs(tokens: Sequence[str]) -> dict[str, float]:
    """Parse leftover ``--symbol value`` tokens into a kwargs dict."""
    kwargs: dict[str, float] = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not token.startswith("--") or len(token) <= 2:
            raise ArgumentError(f"unexpected argument: {token!r}")
        name = token[2:]
        if name in kwargs:
            raise ArgumentError(f"duplicate symbol: --{name}")
        if i + 1 >= len(tokens) or tokens[i + 1].startswith("--"):
            raise ArgumentError(f"--{name} requires a numeric value")
        try:
            kwargs[name] = float(tokens[i + 1])
        except ValueError:
            raise ArgumentError(f"--{name} requires a numeric value") from None
        i += 2
    return kwargs


def _handlers() -> dict:
    return {
        "eval": lambda a: eval_ops.evaluate(a.expr),
        "stat": lambda a: stat_ops.stat(a.op, a.dataset),
        "finance": lambda a: finance_ops.finance(
            a.op,
            pv=a.pv,
            fv=a.fv,
            rate=a.rate,
            periods=a.periods,
            principal=a.principal,
        ),
        "matrix": lambda a: matrix_ops.matrix(a.op, a.matrices),
        "convert-base": lambda a: base_ops.convert(a.value, a.from_base, a.to_base),
        "convert-unit": lambda a: unit_ops.convert(a.value, a.src, a.dst),
        "calculus": lambda a: calculus_ops.calculus(
            a.op, a.expr, a.var, lower=a.lower, upper=a.upper, approach=a.approach
        ),
        "physics-constant": lambda a: physics_ops.constant(a.symbol),
        "physics": lambda a: physics_ops.solve(a.domain, a.solve, a.kwargs),
        "vector": lambda a: vector_ops.vector(a.op, a.vectors),
        "bits": lambda a: bits_ops.bits(
            a.op, a.values, width=a.width, fmt=a.format, signed=a.signed
        ),
        "endian": lambda a: bits_ops.endian(a.op, a.value, width=a.width, order=a.order),
        "hash": lambda a: hash_ops.hash_digest(a.algorithm, a.data, input_format=a.input),
        "crc": lambda a: hash_ops.crc_digest(a.variant, a.data, input_format=a.input),
        "base64": lambda a: hash_ops.base64_code(
            a.op, a.data, urlsafe=a.urlsafe, output_format=a.output
        ),
        "datetime": lambda a: _datetime_handler(a),
        "regex": lambda a: _regex_handler(a),
    }


def _regex_handler(a: argparse.Namespace) -> object:
    """Route the regex subcommand's ops (sub takes pattern+replacement+subject)."""
    if a.op == "sub":
        if len(a.tokens) != 3:
            raise ArgumentError("regex sub takes exactly pattern, replacement, and subject")
        pattern, replacement, subject = a.tokens
        return regex_ops.regex(
            a.op, pattern, subject, flags=a.flags, flavor=a.flavor, replacement=replacement
        )
    if len(a.tokens) != 2:
        raise ArgumentError(f"regex {a.op} takes exactly a pattern and a subject")
    return regex_ops.regex(a.op, a.tokens[0], a.tokens[1], flags=a.flags, flavor=a.flavor)


def _extract_physics_kwargs(argv: Sequence[str]) -> tuple[list[str], dict[str, float]]:
    """Pre-extract dynamic ``--symbol value`` pairs for the physics subcommand.

    argparse cannot know the physics symbols up front (they are registered
    per-domain), so we pull ``--name number`` pairs after the ``physics``
    token out of argv ourselves; everything else is left for argparse.
    """
    try:
        idx = list(argv).index("physics")
    except ValueError:
        return list(argv), {}
    tokens = list(argv)[idx + 1 :]
    kept: list[str] = []
    kwargs: dict[str, float] = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        next_is_value = i + 1 < len(tokens) and not tokens[i + 1].startswith("--")
        reserved = token in ("--solve", "--precision")
        if token.startswith("--") and len(token) > 2 and not reserved and next_is_value:
            try:
                kwargs[token[2:]] = float(tokens[i + 1])
            except ValueError:
                kept.append(token)
                i += 1
                continue
            i += 2
        else:
            kept.append(token)
            i += 1
    return list(argv)[: idx + 1] + kept, kwargs


def _datetime_handler(a: argparse.Namespace) -> object:
    """Route the datetime subcommand's ops; --to defaults to UTC."""
    if a.op == "from-epoch":
        if len(a.timestamps) != 1:
            raise ArgumentError("datetime from-epoch takes exactly 1 timestamp")
        return datetime_ops.from_epoch(a.timestamps[0], tz=a.tz)
    if a.op == "to-epoch":
        if len(a.timestamps) != 1:
            raise ArgumentError("datetime to-epoch takes exactly 1 timestamp")
        return datetime_ops.to_epoch(a.timestamps[0])
    if a.op == "diff":
        if len(a.timestamps) != 2:
            raise ArgumentError("datetime diff takes exactly 2 timestamps")
        return datetime_ops.diff(a.timestamps[0], a.timestamps[1], unit=a.unit or "seconds")
    if a.op == "add":
        if len(a.timestamps) != 1:
            raise ArgumentError("datetime add takes exactly 1 timestamp")
        return datetime_ops.add(
            a.timestamps[0],
            days=a.days,
            hours=a.hours,
            minutes=a.minutes,
            seconds=a.seconds,
            weeks=a.weeks,
            tz=a.tz,
        )
    if a.op == "weekday":
        if len(a.timestamps) != 1:
            raise ArgumentError("datetime weekday takes exactly 1 date")
        return datetime_ops.weekday(a.timestamps[0], tz=a.tz)
    if a.op == "convert-tz":
        if len(a.timestamps) != 1:
            raise ArgumentError("datetime convert-tz takes exactly 1 timestamp")
        return datetime_ops.convert_tz(
            a.timestamps[0], from_tz=a.from_tz, to_tz=a.to_tz or "UTC"
        )
    raise ArgumentError(
        "unknown datetime operation: "
        f"{a.op!r} (expected from-epoch|to-epoch|diff|add|weekday|convert-tz)"
    )


def main(argv: Sequence[str] | None = None) -> int:
    argv = list(sys.argv[1:]) if argv is None else list(argv)
    argv, physics_kwargs = _extract_physics_kwargs(argv)
    parser = _build_parser()
    args, unknown = parser.parse_known_args(argv)
    try:
        if unknown:
            raise ArgumentError(f"unrecognized arguments: {' '.join(unknown)}")
        args.kwargs = physics_kwargs
        result = _handlers()[args.command](args)
    except CalcError as exc:
        print(f"{type(exc).prefix}: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    except BrokenPipeError:
        return 1
    except Exception:  # noqa: BLE001 — defensive: never leak a traceback to stdout
        print("MathError: internal computation failure", file=sys.stderr)
        return 1
    try:
        print(render(result, args.precision))
    except BrokenPipeError:
        return 1
    return 0
