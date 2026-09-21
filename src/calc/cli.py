"""Entry point: parse args, dispatch to a pure handler, render to stdout.

Contract (DESIGN.md 1):
- stdout: ONLY the rendered result (this module is the sole writer);
- stderr: on failure, exactly one line ``<Prefix>: description``;
- exit code: 0 on success, 1 on any domain failure (argparse usage errors
  exit 2 with usage text, documented in the README).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence

from calc.errors import ArgumentError, CalcError
from calc.input_resolver import DEFAULT_MAX_INPUT_BYTES, resolve_all, resolve_token
from calc.ops import (
    assert_ops,
    base_ops,
    bits_ops,
    calculus_ops,
    datetime_ops,
    distribution_ops,
    eval_ops,
    finance_ops,
    gof_ops,
    hash_ops,
    matrix_ops,
    physics_ops,
    regex_ops,
    stat_ops,
    sym_ops,
    unit_ops,
    vector_ops,
)
from calc.render import render

# Tokens shaped like a registered-style long option (`--foo`, `--foo=1`).
# Used by _normalize_positionals: an *unregistered* such token is a typo, not
# a positional (GitHub issue 6), so it is left for argparse to reject.
_LONG_OPTION_PATTERN = re.compile(r"^--[A-Za-z][\w-]*(=.*)?$")


def _build_parser() -> argparse.ArgumentParser:
    precision_parent = argparse.ArgumentParser(add_help=False)
    precision_parent.add_argument(
        "--precision",
        type=int,
        default=None,  # sentinel: None = flag absent (presence checked by R11 guard)
        help="decimal places for float output (default: 4)",
    )

    parser = argparse.ArgumentParser(
        prog="calc",
        description="Deterministic, subcommand-driven CLI math engine for agents.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    max_input_parent = argparse.ArgumentParser(add_help=False)
    max_input_parent.add_argument(
        "--max-input-bytes",
        dest="max_input_bytes",
        type=int,
        default=None,
        help=f"file/stdin input size cap (default {DEFAULT_MAX_INPUT_BYTES})",
    )

    p = sub.add_parser("eval", parents=[precision_parent], help="evaluate a math expression")
    p.add_argument("expr", help="expression, e.g. '2+2' or 'sqrt(2)'")
    p.add_argument(
        "--let",
        action="append",
        default=None,
        metavar="NAME=NUMBER",
        help="bind a numeric variable (repeatable): --let a=2 --let b=3",
    )
    p.add_argument(
        "--exact",
        action="store_true",
        help="exact rational arithmetic (Fraction); prints an integer or p/q",
    )

    p = sub.add_parser(
        "stat",
        parents=[precision_parent, max_input_parent],
        help="statistics over a JSON dataset",
    )
    p.add_argument(
        "op",
        help=(
            "mean|median|mode|stdev|variance|pvariance|sum|min|max|count"
            "|geometric_mean|harmonic_mean"
            "|covariance|pearson|spearman|regression|quantile|rank"
            "|skewness|kurtosis|excess-kurtosis|critical-r"
        ),
    )
    p.add_argument(
        "datasets",
        nargs="*",
        help=(
            "JSON array(s) of numbers: one for univariate ops, X and Y for "
            "covariance|pearson|spearman|regression, plus a q value for quantile"
        ),
    )
    p.add_argument("--ddof", type=int, default=0, help="covariance: 0 (default) or 1")
    p.add_argument(
        "--field",
        default=None,
        help="regression: slope|intercept|r2|stderr|slope_stderr|"
        "residual_stderr|residual_variance; pearson/spearman: "
        "coefficient|p|t|df|n; critical-r: r (the critical |r|)",
    )
    p.add_argument(
        "--alternative",
        default=None,
        choices=["two-sided", "greater", "less"],
        help="pearson/spearman/critical-r: two-sided (default)|greater|less",
    )
    p.add_argument(
        "--alpha",
        type=float,
        default=None,
        help="critical-r: significance level (e.g. 0.05)",
    )
    p.add_argument(
        "--n", type=float, default=None, help="critical-r: sample size (required)"
    )

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
        "matrix",
        parents=[precision_parent, max_input_parent],
        help="matrix operations (JSON matrices)",
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
        "vector",
        parents=[precision_parent, max_input_parent],
        help="vector operations (JSON vectors)",
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

    p = sub.add_parser(
        "hash",
        parents=[precision_parent, max_input_parent],
        help="hash digests",
    )
    p.add_argument("algorithm", help="md5|sha1|sha256|sha512|sha3_256|blake2b")
    p.add_argument(
        "data", help="input text (or hex bytes with --input hex; @file for raw bytes)"
    )
    p.add_argument("--input", default=None, help="input format: text|hex (default text)")

    p = sub.add_parser(
        "crc",
        parents=[precision_parent, max_input_parent],
        help="CRC digests",
    )
    p.add_argument(
        "variant", help="crc32|crc32c|crc16-ccitt-false|crc16-xmodem|crc16-modbus|crc8"
    )
    p.add_argument(
        "data", help="input text (or hex bytes with --input hex; @file for raw bytes)"
    )
    p.add_argument("--input", default=None, help="input format: text|hex (default text)")

    p = sub.add_parser(
        "base64",
        parents=[precision_parent, max_input_parent],
        help="base64 encode/decode",
    )
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
        "regex",
        parents=[precision_parent, max_input_parent],
        help="regex operations (Python dialect only)",
    )
    p.add_argument("op", help="test|findall|groups|sub")
    p.add_argument(
        "tokens", nargs="+", help="pattern + subject (sub: pattern + replacement + subject)"
    )
    p.add_argument("--flags", default=None, help="flag letters, subset of i m s x a")
    p.add_argument("--flavor", default=None, help="regex flavor (v1: python only)")

    p = sub.add_parser(
        "gof",
        parents=[precision_parent, max_input_parent],
        help="goodness-of-fit tests (ks, chi2, chi2-bins); --field required",
    )
    p.add_argument("op", help="ks|chi2|chi2-bins")
    p.add_argument(
        "operands",
        nargs="+",
        help="ks: DATA FAMILY; chi2: OBSERVED EXPECTED; chi2-bins: DATA FAMILY",
    )
    p.add_argument(
        "--bins", type=float, default=None, help="chi2-bins: number of equiprobable bins"
    )
    p.add_argument("--ddof", dest="gof_ddof", type=int, default=0, help="chi2/chi2-bins: ddof")
    p.add_argument(
        "--field",
        required=True,
        help="statistic|p (all ops); df additionally for chi2|chi2-bins",
    )
    for name, helptext in (
        ("alpha", "beta: first shape"),
        ("beta", "beta: second shape"),
        ("mu", "normal/lognormal: mean (of the log for lognormal)"),
        ("sigma", "normal/lognormal: standard deviation"),
        ("low", "uniform: lower bound"),
        ("high", "uniform: upper bound"),
        ("lam", "poisson: rate (ks: rejected)"),
        ("scale", "exponential/gamma: scale"),
        ("shape", "gamma: shape"),
        ("n", "binomial (ks: rejected)"),
        ("p", "binomial (ks: rejected)"),
        ("df", "t/chi2: degrees of freedom (> 0)"),
        ("a", "kumaraswamy: a > 0"),
        ("b", "kumaraswamy: b > 0"),
    ):
        p.add_argument(f"--{name}", type=float, default=None, help=helptext)

    p = sub.add_parser(
        "sym",
        parents=[precision_parent, max_input_parent],
        help="symbolic equivalence, simplify, expand (real domain)",
    )
    p.add_argument("op", help="equiv|simplify|expand")
    p.add_argument("exprs", nargs="+", help="1 expression (simplify|expand) or 2 (equiv)")
    p.add_argument(
        "--var",
        action="append",
        default=None,
        help="declared symbol (repeatable; required for any symbols used)",
    )

    p = sub.add_parser(
        "distribution",
        parents=[precision_parent],
        help="distribution moments, pdf/cdf/ppf/sf, sampling, validation, moments, fit",
        allow_abbrev=False,
    )
    p.add_argument(
        "op",
        help=(
            "describe|mean|variance|stddev|skewness|kurtosis|excess-kurtosis"
            "|pdf|cdf|ppf|sf|sample|validate|compare-moments|fit"
        ),
    )
    p.add_argument(
        "family",
        help=("uniform|beta|normal|lognormal|exponential|gamma|binomial|poisson"
              "|t|chi2|kumaraswamy"),
    )
    p.add_argument(
        "value",
        nargs="?",
        default=None,
        help="pdf/cdf: evaluation point x; ppf: probability q",
    )
    p.add_argument(
        "family2",
        nargs="?",
        default=None,
        help=argparse.SUPPRESS,
    )  # compare-moments second family (after options)
    p.add_argument(
        "--moment",
        default="mean",
        help="compare-moments: mean|variance|stddev|skewness|kurtosis",
    )
    p.add_argument(
        "--family2",
        dest="family2_opt",
        default=None,
        help="compare-moments: second family (explicit preferred form)",
    )
    for name, helptext in (
        ("alpha", "beta: first shape"),
        ("beta", "beta: second shape"),
        ("mu", "normal/lognormal: mean (of the log for lognormal)"),
        ("sigma", "normal/lognormal: standard deviation (of the log for lognormal)"),
        ("low", "uniform: lower bound"),
        ("high", "uniform: upper bound"),
        ("lam", "poisson: rate"),
        ("scale", "exponential/gamma: scale"),
        ("shape", "gamma: shape"),
        ("n", "binomial: trials (non-negative integer)"),
        ("p", "binomial: success probability"),
        ("df", "t/chi2: degrees of freedom (> 0)"),
        ("a", "kumaraswamy: a > 0"),
        ("b", "kumaraswamy: b > 0"),
        ("x", "pdf/cdf: evaluation point (positional preferred)"),
        ("q", "ppf: probability (positional preferred)"),
        ("size", "sample: number of variates"),
        ("seed", "sample: RNG seed (required)"),
        ("alpha2", "second distribution: alpha"),
        ("beta2", "second distribution: beta"),
        ("mu2", "second distribution: mu"),
        ("sigma2", "second distribution: sigma"),
        ("low2", "second distribution: low"),
        ("high2", "second distribution: high"),
        ("lam2", "second distribution: lam"),
        ("scale2", "second distribution: scale"),
        ("shape2", "second distribution: shape"),
        ("n2", "second distribution: n"),
        ("p2", "second distribution: p"),
        ("df2", "second distribution: df"),
        ("a2", "second distribution: a"),
        ("b2", "second distribution: b"),
    ):
        p.add_argument(f"--{name}", type=float, default=None, help=helptext)
    # fit (R9) needs named float/string fields that the loop above cannot give:
    p.add_argument("--mean", type=float, default=None, help="fit: target mean M")
    p.add_argument("--variance", type=float, default=None, help="fit: target variance V")
    p.add_argument(
        "--field",
        dest="fit_param",
        default=None,
        help="fit: fitted parameter name (family-specific)",
    )

    p = sub.add_parser(
        "assert", parents=[precision_parent], help="deterministic assertions (stdout: true)"
    )
    p.add_argument("op", help="approx|equal|between|sign|abs-lt|abs-gt")
    p.add_argument("values", nargs="+", help="numeric operands (sign: value + sign name)")
    p.add_argument("--atol", type=float, default=1e-6, help="approx: absolute tolerance")
    p.add_argument("--rtol", type=float, default=1e-6, help="approx: relative tolerance")

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


def _subparser_option_map(
    parser: argparse.ArgumentParser,
) -> dict[tuple[str, str], argparse.Action]:
    """Map each subcommand's option strings to their actions (R2 preprocessing).

    NOTE: this reaches into argparse's private ``parser._actions`` /
    ``_SubParsersAction.choices`` to enumerate registered options. There is no
    public API for it; this is a deliberate, isolated dependency reviewed
    against the pinned Python/argparse version (3.11/3.12) — re-verify on any
    interpreter upgrade.
    """
    subactions = [
        a for a in parser._actions if isinstance(a, argparse._SubParsersAction)
    ]
    result: dict[tuple[str, str], argparse.Action] = {}
    if not subactions:
        return result
    for choice, subparser in subactions[0].choices.items():
        for action in subparser._actions:
            for opt in action.option_strings:
                result[(choice, opt)] = action
    return result


def _normalize_positionals(
    argv: list[str], option_map: dict[tuple[str, str], argparse.Action]
) -> tuple[list[str], list[str]]:
    """R2: move leading-dash positionals past ``--`` so argparse accepts them.

    argv[0] must be the subcommand (argparse requires it). Tokens after it are
    split into options (matched against the subparser's registered option
    strings, consuming one value for value-taking options; glued
    ``--opt=value`` forms are split on the first ``=``) and positionals
    (everything else, including ``-2+5``, ``-abc``, ``@file``). Rebuild as
    ``<subcmd> <options...> -- <positionals...>``; a user ``--`` forces the
    remainder positional verbatim. If everything is already option-first with
    no leading-dash positional, argv is returned unchanged.

    Returns ``(rebuilt_argv, stray_option_tokens)``. The strays are the
    unregistered long options parked by the issue-6 rule plus their consumed
    values, in original order; the caller reports them verbatim in the
    ``unrecognized arguments`` error (argparse alone would drop the value
    token into a spare positional slot).

    Like ``_subparser_option_map``, this depends on the option map built from
    argparse's private ``_actions`` (see the note there).
    """
    if not argv or argv[0] not in {c for (c, _) in option_map}:
        return argv, []
    cmd = argv[0]
    tokens = argv[1:]
    options: list[str] = []
    positionals: list[str] = []
    i = 0
    saw_double_dash = False
    needs_fix = False
    strays: list[str] = []
    while i < len(tokens):
        token = tokens[i]
        if not saw_double_dash and token == "--":
            saw_double_dash = True
            positionals.extend(tokens[i + 1 :])
            break
        action = None
        glued = False
        if not saw_double_dash:
            action = option_map.get((cmd, token))
            if action is None and token.startswith("--") and "=" in token:
                # glued form --opt=value: classify by the option name only;
                # the token (name=value) passes through unchanged.
                name = token.split("=", 1)[0]
                action = option_map.get((cmd, name))
                glued = action is not None
        if action is not None:
            options.append(token)
            if not glued:
                takes_value = action.nargs is None and not isinstance(
                    action, argparse._StoreConstAction
                )
                if takes_value and i + 1 < len(tokens):
                    options.append(tokens[i + 1])
                    i += 1
            i += 1
            continue
        # A token shaped like a long option that is NOT registered is a typo,
        # never a positional (issue 6): parking it with the options (in front
        # of any ``--`` rebuild) makes argparse report it via ``unrecognized
        # arguments``. Only an explicit user ``--`` separator forces such
        # tokens into positional territory. Single-dash tokens (`-2+5`,
        # `-abc`, `-x`) keep the R2 behavior.
        if not saw_double_dash and _LONG_OPTION_PATTERN.match(token):
            options.append(token)
            strays.append(token)
            needs_fix = True  # force the rebuild: keep the stray out of the positional tail
            # An unregistered long option carries its value with it (issue 6):
            # `--foo 3` must be reported whole, never let `3` fall through as
            # a positional that spare nargs="?" slots could swallow.
            if (
                i + 1 < len(tokens)
                and not _LONG_OPTION_PATTERN.match(tokens[i + 1])
                and not tokens[i + 1].startswith("--")
                and option_map.get((cmd, tokens[i + 1])) is None
            ):
                options.append(tokens[i + 1])
                strays.append(tokens[i + 1])
                i += 1
            i += 1
            continue
        # positional: leading-dash non-options are the R2 hazard
        if token.startswith("-") and len(token) > 1:
            needs_fix = True
        positionals.append(token)
        i += 1
    if not needs_fix:
        return argv, []
    return [cmd, *options, "--", *positionals], strays


def _handlers() -> dict:
    return {
        "eval": lambda a: eval_ops.evaluate(
            a.expr,
            let_bindings=a.let,
            exact=getattr(a, "exact", False),
        ),
        "stat": lambda a: stat_ops.stat_command(
            a.op,
            a.datasets,
            ddof=a.ddof,
            field=a.field,
            alternative=a.alternative,
            alpha=a.alpha,
            n=a.n,
        ),
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
        "hash": lambda a: hash_ops.hash_digest(
            a.algorithm,
            a.data,
            input_format=a.input,
            raw_bytes=_resolved_bytes(a.data, a.max_input_bytes),
        ),
        "crc": lambda a: hash_ops.crc_digest(
            a.variant,
            a.data,
            input_format=a.input,
            raw_bytes=_resolved_bytes(a.data, a.max_input_bytes),
        ),
        "base64": lambda a: hash_ops.base64_code(
            a.op,
            a.data,
            urlsafe=a.urlsafe,
            output_format=a.output,
            raw_bytes=_resolved_bytes(a.data, a.max_input_bytes),
            source_path=_source_path(a.data),
        ),
        "datetime": lambda a: _datetime_handler(a),
        "regex": lambda a: _regex_handler(a),
        "distribution": lambda a: distribution_ops.distribution_command(a),
        "assert": lambda a: assert_ops.assert_command(a.op, a.values, atol=a.atol, rtol=a.rtol),
        "gof": lambda a: gof_ops.gof_command(a),
        "sym": lambda a: sym_ops.sym_command(a),
    }


def _source_path(token: str) -> str | None:
    """The file path behind a ``@<path>`` token, else None (error messages)."""
    if token.startswith("@") and token != "@-":
        return token[1:]
    return None


def _resolved_bytes(token: str, max_input_bytes: int | None) -> bytes | None:
    """Resolve a hash/crc/base64 data token to raw bytes when it is a file/stdin ref.

    Returns ``None`` when the token is not a file reference (``@<path>`` /
    ``@-`` / ``@@`` escape); the op then handles it as text/hex as before.
    """
    if token.startswith("@"):
        cap = (
            max_input_bytes
            if max_input_bytes is not None
            else DEFAULT_MAX_INPUT_BYTES
        )
        return resolve_token(token, binary=True, max_bytes=cap)  # type: ignore[return-value]
    return None


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


_DATA_POSITIONAL_FIELDS = frozenset(
    {
        ("stat", "datasets"),
        ("matrix", "matrices"),
        ("vector", "vectors"),
        ("regex", "tokens"),
        ("gof", "operands"),
        ("sym", "exprs"),
    }
)


def _resolve_cli_inputs(args: argparse.Namespace) -> None:
    """Apply the R3 resolver to data-bearing positionals, in place.

    JSON/text arguments resolve to str; hash/crc/base64 resolve to bytes
    (handled inside the handler via ``_resolved_bytes`` so ``--input hex``
    semantics stay intact). Only one ``@-`` per invocation.
    """
    command = getattr(args, "command", None)
    if command not in {"stat", "matrix", "vector", "regex", "gof", "sym"}:
        return
    for field in ("datasets", "matrices", "vectors", "tokens", "operands", "exprs"):
        values = getattr(args, field, None)
        if values is None:
            continue
        cap = getattr(args, "max_input_bytes", None) or DEFAULT_MAX_INPUT_BYTES
        setattr(args, field, resolve_all(list(values), max_bytes=cap))


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
    argv, stray_options = _normalize_positionals(argv, _subparser_option_map(parser))
    args, unknown = parser.parse_known_args(argv)
    try:
        # Issue 6: strays parked by _normalize_positionals are reported here,
        # verbatim and whole (`--foo 3`), before argparse's own leftovers.
        if stray_options:
            unknown = [*stray_options, *unknown]
        if unknown:
            raise ArgumentError(f"unrecognized arguments: {' '.join(unknown)}")
        if getattr(args, "exact", False) and getattr(args, "precision", None) is not None:
            # R11: --exact and --precision are mutually exclusive regardless of
            # the precision value (the 4 default must be rejected too, so the
            # check is on presence, not on != 4). The precision_parent parser
            # always sets the attribute; it is None only where --precision
            # does not exist (physics suppresses it, defaults are explicit).
            raise ArgumentError("--exact cannot be combined with --precision")
        args.kwargs = physics_kwargs
        _resolve_cli_inputs(args)
        result = _handlers()[args.command](args)
        # Rendering/printing sit INSIDE the defensive handler: a render failure
        # (e.g. the CPython int→str limit on a huge --exact Fraction) must
        # still emit exactly one typed stderr line (INV-2), never a traceback.
        print(render(result, args.precision if args.precision is not None else 4))
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
    return 0
