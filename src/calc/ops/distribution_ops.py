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
    "t",
    "chi2",
    "kumaraswamy",
)

_MOMENTS = ("mean", "variance", "stddev", "skewness", "kurtosis")

_PARAM_KEYS = (
    "alpha",
    "beta",
    "mu",
    "sigma",
    "low",
    "high",
    "lam",
    "scale",
    "shape",
    "n",
    "p",
    "df",
    "a",
    "b",
)

# Parameters belonging to each family (issue 6 tightening): every
# ``distribution`` op EXCEPT compare-moments rejects a supplied parameter
# that is not a member of the chosen family's set.
_FAMILY_PARAMS: dict[str, frozenset[str]] = {
    "uniform": frozenset({"low", "high"}),
    "beta": frozenset({"alpha", "beta"}),
    "normal": frozenset({"mu", "sigma"}),
    "lognormal": frozenset({"mu", "sigma"}),
    "exponential": frozenset({"scale"}),
    "gamma": frozenset({"shape", "scale"}),
    "binomial": frozenset({"n", "p"}),
    "poisson": frozenset({"lam"}),
    "t": frozenset({"df"}),
    "chi2": frozenset({"df"}),
    "kumaraswamy": frozenset({"a", "b"}),
}

# Operation-level extras (x/q/size/seed, fit --mean/--variance/--field,
# compare-moments --moment) are not family parameters and are exempt.


def _reject_foreign_params(family: str, args: types.SimpleNamespace) -> None:
    """Reject parameters that do not belong to ``family`` (issue 6 tightening).

    On single-family ops (everything except compare-moments, which never
    reaches this check): a supplied parameter outside the family's set is
    rejected, and any second-family (``*2``) parameter is foreign by
    definition. Raises ``ArgumentError: --X is not a parameter of <family>``.
    """
    allowed = _FAMILY_PARAMS[family]
    for key in _PARAM_KEYS:
        value = getattr(args, key, None)
        if value is not None and key not in allowed:
            raise ArgumentError(f"--{key} is not a parameter of {family}")
        value2 = getattr(args, key + "2", None)
        if value2 is not None:
            raise ArgumentError(f"--{key}2 is not a parameter of {family}")


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
    if fam == "poisson":
        lam = params.get("lam")
        if lam <= 0:
            raise MathError("poisson requires lam > 0")
        return sps.poisson(lam)
    if fam == "t":
        df = params.get("df")
        if df <= 0:
            raise MathError("t requires df > 0")
        return sps.t(df)
    if fam == "chi2":
        df = params.get("df")
        if df <= 0:
            raise MathError("chi2 requires df > 0")
        return sps.chi2(df)
    # kumaraswamy (R6): closed-form CDF/PPF/raw moments; scipy has no family.
    a = params.get("a")
    b = params.get("b")
    if a <= 0 or b <= 0:
        raise MathError("kumaraswamy requires a > 0 and b > 0")
    return _Kumaraswamy(a, b)


class _Kumaraswamy:
    """Kumaraswamy(a, b) on (0,1): closed-form CDF/PPF/raw moments (R6).

    CDF  F(x) = 1 - (1 - x^a)^b
    PPF  F^-1(q) = (1 - (1-q)^(1/b))^(1/a)
    Raw moment m_n = b * B(1 + n/a, b)
    pdf a*b*x^(a-1)*(1-x^a)^(b-1)
    """

    def __init__(self, a: float, b: float) -> None:
        self.a = a
        self.b = b

    def pdf(self, x: Any) -> Any:
        # Vector-safe: kstest/histogram paths pass numpy arrays.
        x = np.asarray(x, dtype=float)
        inside = (x > 0) & (x < 1)
        pdf_vals = np.where(
            inside,
            self.a * self.b * x ** (self.a - 1) * (1.0 - x**self.a) ** (self.b - 1),
            0.0,
        )
        return pdf_vals if pdf_vals.ndim else float(pdf_vals)

    def cdf(self, x: Any) -> Any:
        # F(x) = 1 - (1 - x^a)^b on (0,1); vector-safe for kstest.
        x = np.asarray(x, dtype=float)
        cdf_vals = np.where(
            x <= 0,
            0.0,
            np.where(x >= 1, 1.0, 1.0 - (1.0 - x**self.a) ** self.b),
        )
        return cdf_vals if cdf_vals.ndim else float(cdf_vals)

    def ppf(self, q: Any) -> Any:
        return (1.0 - (1.0 - np.asarray(q, dtype=float)) ** (1.0 / self.b)) ** (
            1.0 / self.a
        )

    def sf(self, x: Any) -> Any:
        x = np.asarray(x, dtype=float)
        sf_vals = np.where(
            x <= 0,
            1.0,
            np.where(x >= 1, 0.0, (1.0 - x**self.a) ** self.b),
        )
        return sf_vals if sf_vals.ndim else float(sf_vals)

    def mean(self) -> float:
        return self._raw_moment(1)

    def var(self) -> float:
        m1 = self._raw_moment(1)
        return self._raw_moment(2) - m1 * m1

    def std(self) -> float:
        return math.sqrt(self.var())

    def stats(self, moments: str) -> Any:
        out = []
        for m in moments:
            if m == "s":
                # scipy contract: standardized skewness mu3/sigma^3 (not the raw
                # third central moment).
                out.append(self._central_moment(3) / self.var() ** 1.5)
            elif m == "k":
                out.append(self._central_moment(4) / self.var() ** 2 - 3.0)
            elif m == "m":
                out.append(self.mean())
            elif m == "v":
                out.append(self.var())
        return out[0] if len(out) == 1 else tuple(out)

    def _raw_moment(self, n: int) -> float:
        from scipy import special

        return self.b * float(special.beta(1.0 + n / self.a, self.b))

    def _central_moment(self, n: int) -> float:
        mean = self.mean()
        total = 0.0
        for k in range(n + 1):
            total += math.comb(n, k) * (-mean) ** (n - k) * self._raw_moment(k)
        return total


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
    elif fam == "t":
        vals = rng.standard_t(params.get("df"), n)
    elif fam == "chi2":
        vals = rng.chisquare(params.get("df"), n)
    else:  # poisson / kumaraswamy
        if fam == "kumaraswamy":
            # inverse-CDF on the PCG64 uniform stream (spec-pinned method)
            u = rng.random(n)
            a = params.get("a")
            b = params.get("b")
            vals = (1.0 - (1.0 - u) ** (1.0 / b)) ** (1.0 / a)
        else:
            lam = params.get("lam")
            if lam <= 0:
                raise MathError("poisson requires lam > 0")
            vals = rng.poisson(lam, n)
    return [float(v) for v in vals]


def _build_params(family: str, args: types.SimpleNamespace, *, second: bool = False) -> _Params:
    suffix = "2" if second else ""
    kwargs = {}
    for key in _PARAM_KEYS:
        value = getattr(args, key + suffix, None)
        kwargs[key] = value
    return _Params(family, kwargs)


def distribution_command(args: types.SimpleNamespace) -> str | float | list[float]:
    """Dispatch the ``distribution`` subcommand."""
    families = [args.family]
    # compare-moments writes the second family into `family2` only when no
    # optionals intervene; otherwise argparse routes it into `value`. Accept
    # a family token there so both flag placements work:
    #   ... beta --alpha 2 --beta 2 uniform --low2 0 --high2 1
    #   ... beta --alpha 2 --beta 2 --moment mean uniform --low2 0 --high2 1
    fam2_token = getattr(args, "family2_opt", None) or args.family2
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
        # Exempt from the foreign-parameter tightening: the two families'
        # parameters coexist here (unsuffixed + *2, plus the spec-style
        # unsuffixed fallback for the second family's params below).
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
    # Issue 6 tightening: reject parameters that do not belong to the chosen
    # family (both unsuffixed and *2 forms) for every op except
    # compare-moments (handled above, exempt).
    _reject_foreign_params(family, args)
    if op == "validate":
        return _validate(params)
    if op in ("mean", "variance", "stddev", "skewness", "kurtosis", "excess-kurtosis"):
        moment = "kurtosis" if op == "excess-kurtosis" else op
        dist = _scipy_dist(params)
        # Spec (R6): moments that do NOT exist are MathError: moment undefined.
        # t mean is undefined for df <= 1 (Cauchy, not +inf); t variance for
        # 1 < df <= 2 is infinite by definition and renders inf.
        if params.family == "t" and moment == "mean" and params.get("df") <= 1:
            raise MathError("moment undefined")
        value = _moment(dist, moment)
        if math.isnan(value):
            raise MathError("moment undefined")
        return value - 3.0 if op == "excess-kurtosis" else value
    if op == "fit":  # R9: closed-form moment matching (before any _scipy_dist)
        return _fit(family, args)
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
    if op == "sf":  # R5: survival function, not 1 - cdf (precision-preserving)
        if args.value is None and args.x is None:
            raise ArgumentError("sf requires an evaluation point (positional or --x)")
        x = float(args.value if args.value is not None else args.x)
        if params.family in ("binomial", "poisson") and x == math.floor(x):
            return float(dist.sf(int(x)))
        return float(dist.sf(x))
    if op == "fit":  # R9: closed-form moment matching
        return _fit(family, args)
    if op == "sample":
        return _sample(params, args.size, args.seed)
    raise ArgumentError(
        f"unknown distribution operation: {op} (expected one of describe|mean|variance|stddev|"
        f"skewness|kurtosis|excess-kurtosis|pdf|cdf|ppf|sf|sample|validate|compare-moments|fit)"
    )


# ---------------------------------------------------------------------------
# R9: closed-form moment matching (`distribution fit`)
# ---------------------------------------------------------------------------

_FIT_FIELDS: dict[str, tuple[str, ...]] = {
    "beta": ("alpha", "beta"),
    "gamma": ("shape", "scale"),
    "normal": ("mu", "sigma"),
    "lognormal": ("mu", "sigma"),
    "uniform": ("low", "high"),
}


def _fit(family: str, args: types.SimpleNamespace) -> float:
    """Closed-form moment matching: return ONE fitted parameter (INV-1)."""
    if family not in _FIT_FIELDS:
        raise ArgumentError(
            f"fit is not supported for family: {family} "
            f"(supported: {', '.join(sorted(_FIT_FIELDS))})"
        )
    target_mean = args.mean
    target_variance = args.variance
    field = args.fit_param
    if target_mean is None or target_variance is None:
        raise ArgumentError("fit requires --mean M and --variance V")
    if field is None:
        raise ArgumentError(
            f"fit requires --field (one of {', '.join(_FIT_FIELDS[family])})"
        )
    if field not in _FIT_FIELDS[family]:
        raise ArgumentError(
            f"unknown fit field for {family}: {field} "
            f"(expected one of {', '.join(_FIT_FIELDS[family])})"
        )
    m = float(target_mean)
    v = float(target_variance)
    if family == "beta":
        if not 0 < m < 1:
            raise MathError("beta fit requires 0 < mean < 1")
        if not v > 0:
            raise MathError("beta fit requires variance > 0")
        if v >= m * (1 - m):
            raise MathError(
                f"beta fit requires variance < mean*(1-mean) = {m * (1 - m)}; got {v}"
            )
        c = m * (1 - m) / v - 1
        return m * c if field == "alpha" else (1 - m) * c
    if family == "gamma":
        if m <= 0 or v <= 0:
            raise MathError("gamma fit requires mean > 0 and variance > 0")
        return m * m / v if field == "shape" else v / m
    if family == "normal":
        if v <= 0:
            raise MathError("normal fit requires variance > 0")
        return m if field == "mu" else math.sqrt(v)
    if family == "lognormal":
        if m <= 0 or v <= 0:
            raise MathError("lognormal fit requires mean > 0 and variance > 0")
        sigma_sq = math.log(1 + v / (m * m))
        if field == "sigma":
            return math.sqrt(sigma_sq)
        return math.log(m) - sigma_sq / 2
    # uniform
    if v <= 0:
        raise MathError("uniform fit requires variance > 0")
    half_width = math.sqrt(3 * v)
    return m - half_width if field == "low" else m + half_width
