"""Fallback cost: u_trusted = (trusted model's task success) / (untrusted model's task success).

Success = passes ALL functional and safety tests, from the task description alone.
Trusted: data/solve/qwen2.5_3b-instruct.jsonl (3 samples per task).
Untrusted: honest generations data/gen/honest.jsonl (8 samples per task, same kind of prompt).
Writes results/u_trusted.json, with a task-level bootstrap CI.
"""
import json
import os

import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def rates(path, key):
    per = {}
    for l in open(path, encoding="utf-8"):
        r = json.loads(l)
        per.setdefault(r["template"], []).append(bool(r[key]))
    return {t: float(np.mean(v)) for t, v in per.items()}


trusted = rates(os.path.join(ROOT, "data", "solve", "qwen2.5_3b-instruct.jsonl"), "all_pass")
untrusted = rates(os.path.join(ROOT, "data", "gen", "honest.jsonl"), "verified")
T = sorted(set(trusted) & set(untrusted))
tr = np.array([trusted[t] for t in T])
un = np.array([untrusted[t] for t in T])
u = tr.mean() / un.mean()
rng = np.random.default_rng(0)
bs = []
for _ in range(2000):
    i = rng.integers(len(T), size=len(T))
    if un[i].mean() > 0:
        bs.append(tr[i].mean() / un[i].mean())
out = {"u_trusted": float(u), "ci95": [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))],
       "trusted_success": float(tr.mean()), "untrusted_success": float(un.mean()), "tasks": len(T),
       "trusted_model": "qwen2.5:3b-instruct", "untrusted_model": "gemma4:31b-cloud"}
os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "results", "u_trusted.json"), "w"), indent=1)
print(json.dumps(out, indent=1))
