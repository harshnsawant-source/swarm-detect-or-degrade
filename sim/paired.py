"""Paired comparisons between configurations, on the SAME bootstrap template resamples.

Every configuration in a run uses the same list of bootstrap replicates (template resamples), so the difference
between two configurations can be computed replicate by replicate. This removes the between-template variation
the two configurations share, which is most of the width of the unpaired intervals.

Usage: python sim/paired.py <tag>      -> results/<tag>/paired.json
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TAG = sys.argv[1]
RES = os.path.join(ROOT, "results", TAG)


def rows(name):
    path = os.path.join(RES, f"{name}.json")
    return json.load(open(path))["rows"] if os.path.exists(path) else []


def get(name, metric, **cfg):
    for r in rows(name):
        if all(r.get(k) == v for k, v in cfg.items()) and "reps" in r:
            return np.array([np.nan if x is None else x for x in r["reps"][metric]], dtype=float)
    return None


def diff(a, b):
    """Mean and 95% percentile interval of a - b over replicates where both are defined; P(a - b > 0)."""
    if a is None or b is None:
        return None
    m = ~np.isnan(a) & ~np.isnan(b)
    d = a[m] - b[m]
    if not len(d):
        return None
    return {"mean": float(d.mean()), "ci95": [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))],
            "p_positive": float(np.mean(d > 0)), "n": int(len(d))}


def main():
    protos = sorted({r["proto"] for r in rows("detect")})
    out = {}
    for p in protos:
        # flood effect: safety at D (flood) minus safety without decoys, same protocol
        for D in (50, 100, 200):
            out[f"detect {p}: D{D} - D0 (safety)"] = diff(get("detect", "safety", proto=p, D=D),
                                                           get("detect", "safety", proto=p, D=0))
        # degrade effect
        out[f"degrade {p}: D100 - D0 (usefulness)"] = diff(get("degrade", "usefulness", proto=p, D=100),
                                                            get("degrade", "usefulness", proto=p, D=0))
        # swarm effect: many identities vs one
        for k in (20, 40):
            out[f"swarm {p}: k{k} - k5 (safety)"] = diff(get("swarm", "safety", proto=p, k=k),
                                                         get("swarm", "safety", proto=p, k=5))
    # protocol comparisons under the same attack
    for a, b in (("cascade", "defer"), ("cascade", "local"), ("ours", "local"), ("local", "defer")):
        for D in (100, 200):
            out[f"detect D{D}: {a} - {b} (safety)"] = diff(get("detect", "safety", proto=a, D=D),
                                                          get("detect", "safety", proto=b, D=D))
        for k in (5, 20, 40):
            out[f"swarm k{k}: {a} - {b} (safety)"] = diff(get("swarm", "safety", proto=a, k=k),
                                                         get("swarm", "safety", proto=b, k=k))
    out = {k: v for k, v in out.items() if v is not None}
    json.dump(out, open(os.path.join(RES, "paired.json"), "w"), indent=1)
    for k, v in out.items():
        print(f"{k:45s} {v['mean']:+.2f}  [{v['ci95'][0]:+.2f}, {v['ci95'][1]:+.2f}]  P(>0)={v['p_positive']:.2f}")


if __name__ == "__main__":
    main()
