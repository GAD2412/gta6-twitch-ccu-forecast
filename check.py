"""Leave-one-out check: forecast each comparable launch from the others and compare with the house baseline.

    python3 check.py path/to/p00.in
"""
import json, math, sys
from main import curves, forecast

def loss(fc, day):
    tot = n = 0
    for r in fc["hours"]:
        y = max(day[r["hour"] - 1], 1)
        for tau, q in zip([.05, .25, .5, .75, .95], r["q"]):
            d = math.log(y) - math.log(q); tot += 2 * max(tau * d, (tau - 1) * d); n += 1
    return tot / n

cs = curves(json.load(open(sys.argv[1]))["comparables"])
mine = base = 0
for i, (_, l) in enumerate(cs):
    day = [100.0] + [100.0 * math.exp(x) for x in l]
    mine += loss(forecast(100.0, cs[:i] + cs[i + 1:]), day)
    base += loss(forecast(100.0, []), day)
print(f"launches={len(cs)} model={mine / len(cs):.4f} baseline={base / len(cs):.4f}")
assert mine < base, "model must beat the house baseline"
