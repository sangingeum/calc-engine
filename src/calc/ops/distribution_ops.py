"""``distribution`` command: 8 families, deterministic analytics and sampling.

Parameterizations (all documented in SKILL.md):
- uniform:  low < high                 (pdf 1/(high-low) on [low, high])
- beta:     alpha > 0, beta > 0        (shape/shape)
- normal:   mu (any), sigma > 0
- lognormal: mu (any), sigma > 0       (log X ~ Normal(mu, sigma^2))
- exponential: scale > 0               (rate = 1/scale)
- gamma:    shape > 0, scale > 0
- binomial: n >= 0 integer, 0 <= p <= 1
- poisson:  lam > 0

Conventions (SKILL.md):
- kurtosis: non-excess (fourth standardized moment, normal = 3);
  excess-kurtosis = kurtosis - 3.
- sample: numpy PCG64 (numpy>=1.26,<2) seeded with ``--seed``; integer-seeded
  Generator.default_rng streams are stable across releases/environments.
- compare-moments: boolean exit-style result — prints ``true``/``false`` for
  the requested moment of two families under the one-value stdout contract.
"""

from __future__ import annotations

import math
import types
from typing import Any

import numpy as np
from scipy import stats as sps

from calc.errors import ArgumentError, MathError

_FAMILIES = (
    "uniform",
    "beta",
    "normal",
    "lognormal",
    "exponential",
    "gamma",
    "binomial",
    "poisson",
)

_MOMENTS = ("mean", "variance", "stddev", "skewness", "kurtosis")

_PARAM_KEYS = ("alpha", "beta", "mu", "sigma", "low", "high", "lam", "scale", "shape", "n", "p")


class _Params:
    """Validated parameter set for one family."""

    def __init__(self, family: str, kwargs: dict[str, float | None]) -> None:
        self.family = family
        self.kw = {k: v for k, v in kwargs.items() if v is not None}

    def get(self, name: str) -> float:
        value = self.kw.get(name)
        if value is None:
            raise ArgumentError(f"{self.family} requires --{name}")
        return float(value)


def _scipy_dist(params: _Params) -> Any:
    """Map our parameterization onto the matching frozen scipy distribution."""
    fam = params.family
    if fam == "uniform":
        low = params.get("low")
        high = params.get("high")
        if not low < high:
            raise MathError("uniform requires low < high")
        return sps.uniform(loc=low, scale=high - low)
    if fam == "beta":
        alpha = params.get("alpha")
        beta = params.get("beta")
        if alpha <= 0 or beta <= 0:
            raise MathError("beta requires alpha > 0 and beta > 0")
        return sps.beta(alpha, beta)
    if fam == "normal":
        sigma = params.get("sigma")
        if sigma <= 0:
            raise MathError("normal requires sigma > 0")
        return sps.norm(loc=params.get("mu"), scale=sigma)
    if fam == "lognormal":
        sigma = params.get("sigma")
        if sigma <= 0:
            raise MathError("lognormal requires sigma > 0")
        return sps.lognorm(s=sigma, scale=math.exp(params.get("mu")))
    if fam == "exponential":
        scale = params.get("scale")
        if scale <= 0:
            raise MathError("exponential requires scale > 0")
        return sps.expon(scale=scale)
    if fam == "gamma":
        shape = params.get("shape")
        scale = params.get("scale")
        if shape <= 0 or scale <= 0:
            raise MathError("gamma requires shape > 0 and scale > 0")
        return sps.gamma(a=shape, scale=scale)
    if fam == "binomial":
        n = params.get("n")
        if n < 0 or n != math.floor(n):
            raise MathError("binomial requires n to be a non-negative integer")
        p = params.get("p")
        if not 0 <= p <= 1:
            raise MathError("binomial requires 0 <= p <= 1")
        return sps.binom(int(n), p)
    # poisson
    lam = params.get("lam")
    if lam <= 0:
        raise MathError("poisson requires lam > 0")
    return sps.poisson(lam)


def _moment(dist: Any, moment: str) -> float:
    if moment == "mean":
        return float(dist.mean())
    if moment == "variance":
        return float(dist.var())
    if moment == "stddev":
        return float(dist.std())
    if moment == "skewness":
        return float(dist.stats(moments="s"))
    # kurtosis: non-excess (normal = 3)
    return float(dist.stats(moments="k")) + 3.0


def _validate(params: _Params) -> str:
    """Raise a typed domain error on invalid parameters; return 'true' otherwise."""
    _scipy_dist(params)  # validates parameter-domain constraints
    return "true"


def _sample(params: _Params, size: float | None, seed: float | None) -> list[float]:
    """Deterministic sampling via numpy PCG64; no implicit time source."""
    if size is None:
        raise ArgumentError("sample requires --size")
    if seed is None:
        raise ArgumentError("sample requires --seed")
    n = int(size)
    if n < 0:
        raise MathError("size must be non-negative")
    rng = np.random.default_rng(int(seed))
    fam = params.family
    vals: Any
    if fam == "uniform":
        vals = rng.uniform(params.get("low"), params.get("high"), n)
    elif fam == "beta":
        vals = rng.beta(params.get("alpha"), params.get("beta"), n)
    elif fam == "normal":
        vals = rng.normal(params.get("mu"), params.get("sigma"), n)
    elif fam == "lognormal":
        vals = rng.lognormal(params.get("mu"), params.get("sigma"), n)
    elif fam == "exponential":
        vals = rng.exponential(params.get("scale"), n)
    elif fam == "gamma":
        vals = rng.gamma(params.get("shape"), params.get("scale"), n)
    elif fam == "binomial":
        vals = rng.binomial(int(params.get("n")), params.get("p"), n)
    else:  # poisson
        vals = rng.poisson(params.get("lam"), n)
    return [float(v) for v in vals]


def _build_params(family: str, args: types.SimpleNamespace, *, second: bool = False) -> _Params:
    suffix = "2" if second else ""
    kwargs = {key: getattr(args, key + suffix) for key in _PARAM_KEYS}
    return _Params(family, kwargs)


def distribution_command(args: types.SimpleNamespace) -> str | float | list[float]:
    """Dispatch the ``distribution`` subcommand."""
    families = [args.family]
    # compare-moments writes the second family into `family2` only when no
    # optionals intervene; otherwise argparse routes it into `value`. Accept
    # a family token there so both flag placements work:
    #   ... beta --alpha 2 --beta 2 uniform --low2 0 --high2 1
    #   ... beta --alpha 2 --beta 2 --moment mean uniform --low2 0 --high2 1
    fam2_token = args.family2
    if fam2_token is None and args.value is not None and args.value in _FAMILIES:
        fam2_token = args.value
    if fam2_token is not None:
        families.append(fam2_token)
    if len(families) > 2:
        raise ArgumentError("distribution takes at most 2 families (compare-moments)")
    family = families[0]
    if family not in _FAMILIES:
        raise ArgumentError(
            f"unknown distribution family: {family} (expected one of {', '.join(_FAMILIES)})"
        )
    op = args.op
    if op == "compare-moments":
        if len(families) != 2:
            raise ArgumentError("compare-moments takes exactly 2 families")
        fam2 = families[1]
        if fam2 not in _FAMILIES:
            raise ArgumentError(
                f"unknown distribution family: {fam2} (expected one of {', '.join(_FAMILIES)})"
            )
        moment = args.moment
        if moment not in _MOMENTS:
            raise ArgumentError(
                f"unknown moment: {moment} (expected one of {', '.join(_MOMENTS)})"
            )
        p1 = _build_params(family, args)
        p2 = _build_params(fam2, args, second=True)
        # Tolerate the spec-style placement where the second family's params
        # arrive via the unsuffixed flags (argparse positional fallback):
        # `beta --alpha 2 --beta 2 uniform --low 0 --high 1`.
        if fam2 == "uniform" and args.low2 is None and args.low is not None:
            p2.kw = {"low": args.low, "high": args.high}
        elif (
            fam2 == "beta"
            and args.alpha2 is None
            and args.alpha is not None
            and args.beta is not None
        ):
            p2.kw = {"alpha": args.alpha, "beta": args.beta}
        m1 = _moment(_scipy_dist(p1), moment)
        m2 = _moment(_scipy_dist(p2), moment)
        return "true" if math.isclose(m1, m2, rel_tol=1e-12, abs_tol=1e-12) else "false"

    params = _build_params(family, args)
    if op == "validate":
        return _validate(params)
    if op in ("mean", "variance", "stddev", "skewness", "kurtosis", "excess-kurtosis"):
        moment = "kurtosis" if op == "excess-kurtosis" else op
        value = _moment(_scipy_dist(params), moment)
        return value - 3.0 if op == "excess-kurtosis" else value
    dist = _scipy_dist(params)
    if op == "describe":
        # single-value stdout contract: reject instead of structured output
        raise ArgumentError(
            "describe would emit structured output; use mean|variance|stddev individually"
        )
    if op == "pdf":
        if args.value is None and args.x is None:
            raise ArgumentError("pdf requires an evaluation point (positional or --x)")
        x = float(args.value if args.value is not None else args.x)
        return float(dist.pdf(x))
    if op == "cdf":
        if args.value is None and args.x is None:
            raise ArgumentError("cdf requires an evaluation point (positional or --x)")
        x = float(args.value if args.value is not None else args.x)
        return float(dist.cdf(x))
    if op == "ppf":
        if args.value is None and args.q is None:
            raise ArgumentError("ppf requires a probability (positional or --q)")
        q = float(args.value if args.value is not None else args.q)
        if not 0 <= q <= 1:
            raise MathError("q must be in [0, 1]")
        return float(dist.ppf(q))
    if op == "sample":
        return _sample(params, args.size, args.seed)
    raise ArgumentError(
        f"unknown distribution operation: {op} (expected one of describe|mean|variance|stddev|"
        f"skewness|kurtosis|excess-kurtosis|pdf|cdf|ppf|sample|validate|compare-moments)"
    )
