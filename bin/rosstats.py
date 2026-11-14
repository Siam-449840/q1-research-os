"""Statistical-reporting consistency checker (statcheck-style), stdlib only.

Finds APA-style results such as ``t(23) = 2.45, p = .021``, ``F(2, 57) = 4.1, p < .05``,
``χ2(1) = 3.84, p = .05``, ``r(40) = .31, p = .045`` or ``z = 1.96, p = .05``, recomputes the
two-tailed p-value from the test statistic and degrees of freedom, and reports inconsistencies.
Rounding of the reported statistic and p-value is allowed for.
"""

from __future__ import annotations

import math
import re
from typing import List, NamedTuple, Optional, Tuple

_EPS = 3e-14
_MAX_ITER = 300

RESULT_RE = re.compile(
    r"(?P<test>\bt|\bF|χ2|χ²|\bchi2|\bchi-square|\br|\bz)\s*"
    r"(?:\(\s*(?P<df1>\d+(?:\.\d+)?)\s*(?:,\s*(?P<df2>\d+(?:\.\d+)?))?\s*\))?\s*"
    r"=\s*(?P<stat>[-−]?\d*\.?\d+)\s*,\s*p\s*(?P<cmp>[<>=≤≥])\s*(?P<p>0?\.\d+|1(?:\.0+)?)",
    re.I,
)


class StatResult(NamedTuple):
    line: int
    text: str
    reported: str
    computed_low: float
    computed_high: float
    consistent: bool
    decision_error: bool


def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (Lentz)."""
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
    h = d
    for m in range(1, _MAX_ITER + 1):
        m2 = 2 * m
        for aa in (m * (b - m) * x / ((qam + m2) * (a + m2)), -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))):
            d = 1.0 + aa * d
            d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
            c = 1.0 + aa / c
            c = c if abs(c) > 1e-300 else 1e-300
            h *= d * c
        if abs(d * c - 1.0) < _EPS:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_front = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(ln_front) * _betacf(a, b, x) / a
    return 1.0 - math.exp(ln_front) * _betacf(b, a, 1.0 - x) / b


def gammaincc(s: float, x: float) -> float:
    """Regularized upper incomplete gamma Q(s, x)."""
    if x <= 0.0:
        return 1.0
    if x < s + 1.0:  # series for P, then Q = 1 - P
        term = total = 1.0 / s
        n = s
        for _ in range(_MAX_ITER):
            n += 1.0
            term *= x / n
            total += term
            if abs(term) < abs(total) * _EPS:
                break
        return 1.0 - total * math.exp(-x + s * math.log(x) - math.lgamma(s))
    b, c, d = x + 1.0 - s, 1e300, 1.0 / (x + 1.0 - s)
    h = d
    for i in range(1, _MAX_ITER + 1):
        an = -i * (i - s)
        b += 2.0
        d = an * d + b
        d = 1.0 / (d if abs(d) > 1e-300 else 1e-300)
        c = b + an / c
        c = c if abs(c) > 1e-300 else 1e-300
        h *= d * c
        if abs(d * c - 1.0) < _EPS:
            break
    return math.exp(-x + s * math.log(x) - math.lgamma(s)) * h


def p_value(test: str, stat: float, df1: Optional[float], df2: Optional[float]) -> Optional[float]:
    """Two-tailed p for t, r, z; upper tail for F and chi-square."""
    t = test.lower()
    if t == "z":
        return math.erfc(abs(stat) / math.sqrt(2.0))
    if t == "r":
        if df1 is None or abs(stat) >= 1.0:
            return None
        t, stat = "t", stat * math.sqrt(df1 / (1.0 - stat * stat))
    if t == "t":
        if df1 is None or df1 <= 0:
            return None
        return betainc(df1 / 2.0, 0.5, df1 / (df1 + stat * stat))
    if t == "f":
        if df1 is None or df2 is None or stat < 0:
            return None
        return betainc(df2 / 2.0, df1 / 2.0, df2 / (df2 + df1 * stat))
    if df1 is None or stat < 0:  # chi-square family
        return None
    return gammaincc(df1 / 2.0, stat / 2.0)


def _p_range(test: str, stat_tok: str, df1: Optional[float], df2: Optional[float]) -> Optional[Tuple[float, float]]:
    stat = float(stat_tok.replace("−", "-"))
    half = 0.5 * 10 ** -(len(stat_tok.split(".")[1]) if "." in stat_tok else 0)
    lo_stat, hi_stat = abs(stat) - half, abs(stat) + half
    if test.lower() == "r":
        hi_stat = min(hi_stat, 0.999999)
    ps = [p_value(test, max(v, 0.0), df1, df2) for v in (lo_stat, hi_stat)]
    if any(p is None for p in ps):
        return None
    return min(ps), max(ps)


def _consistent(cmp: str, p_tok: str, lo: float, hi: float) -> bool:
    reported = float(p_tok)
    tol = 0.5 * 10 ** -len(p_tok.split(".")[1]) if "." in p_tok else 0.5
    if cmp in "<≤":
        return lo < reported + 1e-12
    if cmp in ">≥":
        return hi > reported - 1e-12
    return lo - tol <= reported <= hi + tol


def check_text(text: str, alpha: float = 0.05) -> List[StatResult]:
    out: List[StatResult] = []
    for ln, line in enumerate(text.splitlines(), 1):
        for m in RESULT_RE.finditer(line):
            test = m.group("test").replace("χ²", "chi2").replace("χ2", "chi2")
            df1 = float(m.group("df1")) if m.group("df1") else None
            df2 = float(m.group("df2")) if m.group("df2") else None
            rng = _p_range(test, m.group("stat"), df1, df2)
            if rng is None:
                continue
            lo, hi = rng
            ok = _consistent(m.group("cmp"), m.group("p"), lo, hi)
            reported_sig = float(m.group("p")) <= alpha if m.group("cmp") in "=<≤" else False
            computed_sig = hi <= alpha
            out.append(StatResult(ln, m.group(0), f"p {m.group('cmp')} {m.group('p')}", lo, hi, ok,
                                  (not ok) and reported_sig != computed_sig))
    return out
