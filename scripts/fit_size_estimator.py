"""
Fit the "Find my size" body estimator (frontend/public/size-estimator.js).

Estimates chest, waist and hip circumference from what a shopper can type in ten
seconds: height, weight and (optionally) age. Fitted on ANSUR II, the public US Army
anthropometric survey (4,082 men, 1,986 women, measured 2010-2012), using the
SELF-REPORTED height and weight columns as inputs, because that is what a shopper gives
us: people overstate height and understate weight, and fitting on their own answers
absorbs that.

    python3 scripts/fit_size_estimator.py <dir with the two "ANSUR II ... Public.csv" files>

Prints the JSON block that is pasted into size-estimator.js, plus cross-validated
accuracy. Needs pandas and numpy. The CSVs are not in the repo (about 3 MB); they are
published by the US Army at https://www.openlab.psu.edu/ansur2/.

What the numbers mean
  coef       cm = b0 + bh*height_cm + bw*weight_kg (+ ba*age)
  sd         residual SD (cm) of that fit, 5-fold cross-validated
  shift      mean residual of the lower / upper third: how far a person who is
             "slimmer / fuller here than most people of my height and weight" sits
             from the estimate. The widget's shape questions move the estimate by a
             fraction of this.
  cross      how the OTHER measurements move, on average, for people in the lower /
             upper third of this one.

Limits (also stated in size-estimator.js)
  - Soldiers aged 17-58: leaner and more muscular than shoppers in general, and nobody
    over 58. Outside the sampled range the estimate is an extrapolation.
  - "waist" is measured at the navel. That matches where men's trousers sit; it is NOT
    the natural waist women's size charts use, so the widget does not use it for women.
"""
import json
import sys

import numpy as np
import pandas as pd

TARGETS = {"chest": "chestcircumference", "waist": "waistcircumference", "hips": "buttockcircumference"}
# Europe bands from sizing-engine.js, to report size agreement.
BANDS = {"male": {"chest": [86, 94, 100, 108, 116, 124], "waist": [74, 82, 90, 98, 108, 118], "hips": [90, 96, 102, 108, 116, 124]},
         "female": {"chest": [80, 88, 94, 102, 112, 124], "waist": [64, 70, 78, 86, 96, 108], "hips": [88, 96, 102, 110, 118, 128]}}


def load(path):
    d = pd.read_csv(path, encoding="latin-1")
    x = pd.DataFrame({
        "h": d.Heightin * 2.54, "w": d.Weightlbs * 0.45359237, "age": d.Age.astype(float),
        **{k: d[c] / 10 for k, c in TARGETS.items()},
    })
    return x[(x.w > 35) & (x.h > 135)].reset_index(drop=True)


def design(x, with_age):
    cols = [np.ones(len(x)), x.h.values, x.w.values] + ([x.age.values] if with_age else [])
    return np.column_stack(cols)


def cv_residuals(x, target, with_age, k=5, seed=0):
    idx = np.random.default_rng(seed).permutation(len(x))
    X, y, res = design(x, with_age), x[target].values, np.zeros(len(x))
    for fold in np.array_split(idx, k):
        train = np.setdiff1d(idx, fold)
        beta, *_ = np.linalg.lstsq(X[train], y[train], rcond=None)
        res[fold] = y[fold] - X[fold] @ beta
    return res


def size_of(v, band):
    return np.searchsorted(np.array(band), v, side="left").clip(0, 5)


def main(folder):
    out = {}
    for gender, fname in (("male", "ANSUR II MALE Public.csv"), ("female", "ANSUR II FEMALE Public.csv")):
        x = load(f"{folder}/{fname}")
        g = {"n": len(x), "range": {k: [round(float(x[k].quantile(0.005)), 1), round(float(x[k].quantile(0.995)), 1)] for k in ("h", "w", "age")}}
        res = {t: cv_residuals(x, t, True) for t in TARGETS}
        for t in TARGETS:
            entry = {}
            for with_age, key in ((True, "age"), (False, "noage")):
                beta, *_ = np.linalg.lstsq(design(x, with_age), x[t].values, rcond=None)
                r = cv_residuals(x, t, with_age)
                entry[key] = {"coef": [round(float(b), 5) for b in beta], "sd": round(float(r.std()), 2)}
                pred = x[t].values - r
                exact = np.mean(size_of(x[t].values, BANDS[gender][t]) == size_of(pred, BANDS[gender][t]))
                within = np.mean(abs(size_of(x[t].values, BANDS[gender][t]) - size_of(pred, BANDS[gender][t])) <= 1)
                print(f"{gender:6s} {t:5s} {key:5s} sd {r.std():.2f} cm | same size as measured {exact*100:.0f}% | within one size {within*100:.1f}%", file=sys.stderr)
            r = res[t]
            lo, hi = np.quantile(r, [1 / 3, 2 / 3])
            low, high = r < lo, r > hi
            entry["shift"] = [round(float(r[low].mean()), 2), round(float(r[high].mean()), 2)]
            entry["sd_within_third"] = round(float(np.sqrt((r[low].var() + r[high].var() + r[~low & ~high].var()) / 3)), 2)
            entry["cross"] = {o: [round(float(res[o][low].mean()), 2), round(float(res[o][high].mean()), 2)] for o in TARGETS if o != t}
            g[t] = entry
        out[gender] = g
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
