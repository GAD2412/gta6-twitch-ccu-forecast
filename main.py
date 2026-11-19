"""GTA VI launch-day Twitch viewers, hours 2..24, as quantiles (make.fun gta6-twitch-ccu-forecast-01).

Analog forecast: every comparable launch in the case gives a release-day curve, log(hour h / hour 1).
Hour h's quantiles are weighted empirical quantiles of those log ratios across launches, applied to this
case's hour-1 print. Stdlib only, deterministic. check.py scores it leave-one-out against the house baseline.
"""

import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path

INPUT_DIR = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
LEVELS = [0.05, 0.25, 0.5, 0.75, 0.95]
Z = [-1.645, -0.674, 0.0, 0.674, 1.645]
MIN_SD = 0.05  # floor on the log spread per sqrt(hour)
SLOPE_SHRINK = 0.5  # momentum slope, halved (LOO full slope: better on midnight-local launches, worse on all)
# Tried and dropped (leave-one-out loss, lower is better): plain 0.713; widen x1.2 0.717; IQR-normal tails 0.761;
# kernel-weighting analogs by pre-launch shape 0.750. Kept: per-hour regression on momentum log(h1 / 6h before),
# slope x0.5: midnight-local launches 0.327 -> 0.307, all launches 0.731 -> 0.726. 1h/12h/24h windows did not help.


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def weight(c):
    u = (str(c.get("unlock") or "") + " " + str(c.get("source") or "")).lower()
    w = 1.0
    if "midnight local" in u:  # GTA VI unlocks at midnight local (NZ 11:00Z .. US Eastern 05:00Z)
        w *= 6.0  # LOO on midnight-local launches: x1.5 0.374, x6 0.327, only-these 0.324
    if "early access" in u or "early-access" in u:
        w *= 0.5
    if "tier: weak" in u or "f2p" in u:
        w *= 0.3
    return w


def curves(comparables):
    """[(weight, [log(h/h1) for h in 2..24], momentum)] for every launch with a full release day."""
    out = []
    for c in comparables:
        if str(c.get("unlock") or "").lower().startswith("not a launch"):
            continue
        d0 = ts(c["day_start"])
        v = {ts(r["from"]): r["viewers"] for r in c["hourly"] if r.get("viewers")}
        day = [v.get(d0 + timedelta(hours=k)) for k in range(24)]
        if any(x is None or x <= 0 for x in day):
            continue
        out.append((weight(c), [math.log(day[k] / day[0]) for k in range(1, 24)], momentum(day[0], v.get(d0 - timedelta(hours=6)))))
    return out


def momentum(p1, p_6):
    """log(hour 1 / the hour 6 hours before it): how much of the launch's early surge has already arrived."""
    return math.log(max(p1, 1) / p_6) if p_6 and p_6 > 0 else None


def target_momentum(case, p1):
    try:  # odd history must never crash the case: fall back to the plain analog quantiles
        d0 = ts(case["day_start"]) - timedelta(hours=6)
        return momentum(p1, next((r["viewers"] for r in case.get("history_hourly") or [] if ts(r["from"]) == d0), None))
    except (KeyError, TypeError, ValueError):
        return None


def wquantile(pairs, tau):
    """Weighted quantile of [(value, weight)], linear between mid-point cumulative weights."""
    pairs = sorted(pairs)
    total = sum(w for _, w in pairs)
    cum, pts = 0.0, []
    for x, w in pairs:
        pts.append(((cum + w / 2) / total, x))
        cum += w
    if tau <= pts[0][0]:
        return pts[0][1]
    for (p0, x0), (p1, x1) in zip(pts, pts[1:]):
        if tau <= p1:
            return x0 + (x1 - x0) * (tau - p0) / (p1 - p0)
    return pts[-1][1]


def forecast(p1, cs, f=None):
    p1 = max(p1, 1.0)
    fit = [c for c in cs if len(c) > 2 and c[2] is not None] if f is not None else []
    rows = []
    for i in range(23):
        hour = i + 2
        if len(fit) >= 5:  # residual quantiles around a weighted momentum regression
            W = sum(c[0] for c in fit)
            mx = sum(c[0] * c[2] for c in fit) / W
            my = sum(c[0] * c[1][i] for c in fit) / W
            sxx = sum(c[0] * (c[2] - mx) ** 2 for c in fit)
            b = SLOPE_SHRINK * sum(c[0] * (c[2] - mx) * (c[1][i] - my) for c in fit) / sxx if sxx > 0 else 0.0
            pairs = [(c[1][i] - b * (c[2] - mx), c[0]) for c in fit]
            shift = b * (f - mx)
            med = wquantile(pairs, 0.5) + shift
            qs = [wquantile(pairs, t) + shift for t in LEVELS]
        elif cs:
            pairs = [(c[1][i], c[0]) for c in cs]
            med = wquantile(pairs, 0.5)
            qs = [wquantile(pairs, t) for t in LEVELS]
        else:  # no analogs: the house baseline's random walk
            med, qs = 0.0, [z * 0.15 * math.sqrt(hour - 1) for z in Z]
        sd = MIN_SD * math.sqrt(hour - 1)
        qs = [min(q, med + z * sd) if z < 0 else max(q, med + z * sd) for q, z in zip(qs, Z)]
        vals, prev = [], 0.0
        for q in qs:
            prev = max(prev, round(min(p1 * math.exp(q), 1e9), 2), 0.01)
            vals.append(prev)
        rows.append({"hour": hour, "q": vals})
    return {"hours": rows}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for f in sorted(INPUT_DIR.glob("*.in")):
        case = json.loads(f.read_text(encoding="utf-8"))
        p1 = float(case["known"][0]["viewers"] or 1)
        out = forecast(p1, curves(case.get("comparables") or []), target_momentum(case, p1))
        (OUTPUT_DIR / (f.stem + ".out")).write_text(json.dumps(out), encoding="utf-8")


if __name__ == "__main__":
    main()
