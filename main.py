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
# Tried and dropped (leave-one-out loss, lower is better): plain 0.713; widen x1.2 0.717; IQR-normal tails 0.761;
# kernel-weighting analogs by pre-launch shape 0.750.


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
    """[(weight, [log(h/h1) for h in 2..24])] for every launch with a full release day."""
    out = []
    for c in comparables:
        if str(c.get("unlock") or "").lower().startswith("not a launch"):
            continue
        d0 = ts(c["day_start"])
        v = {ts(r["from"]): r["viewers"] for r in c["hourly"] if r.get("viewers")}
        day = [v.get(d0 + timedelta(hours=k)) for k in range(24)]
        if any(x is None or x <= 0 for x in day):
            continue
        out.append((weight(c), [math.log(day[k] / day[0]) for k in range(1, 24)]))
    return out


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


def forecast(p1, cs):
    p1 = max(p1, 1.0)
    rows = []
    for i in range(23):
        hour = i + 2
        if cs:
            pairs = [(l[i], w) for w, l in cs]
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
        out = forecast(p1, curves(case.get("comparables") or []))
        (OUTPUT_DIR / (f.stem + ".out")).write_text(json.dumps(out), encoding="utf-8")


if __name__ == "__main__":
    main()
