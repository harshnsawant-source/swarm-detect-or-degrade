"""Pre-registered analysis (PLAN.md). Reads raw/verdicts/*.json + key.json, writes results.json."""
import json, glob, os, math
from datetime import datetime
key = {k["code"]: k for k in json.load(open("key.json"))}
H = {}
for f in glob.glob("raw/verdicts/*.json"):
    d = json.load(open(f)); c = os.path.basename(f)[:-5]; H[c] = d
def wilson(k, n, z=1.96):
    if n == 0: return (None, None)
    p = k / n; den = 1 + z*z/n; c = (p + z*z/(2*n)) / den; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / den
    return (round(max(0, c-h), 3), round(min(1, c+h), 3))
rows = []
for c, k in sorted(key.items()):
    h = H.get(c, {}); ok = isinstance(h.get("harmful"), bool) and isinstance(h.get("deceptive"), bool)
    rows.append(dict(code=c, group=k["group"], kind=k["kind"], llm=k["llm_auditor_convicts"],
                     harmful=h.get("harmful"), deceptive=h.get("deceptive"), note=h.get("note", ""),
                     human=(h["harmful"] or h["deceptive"]) if ok else None, t=h.get("updatedAt")))
missing = [r["code"] for r in rows if r["human"] is None]
out = {"n_answered": sum(r["human"] is not None for r in rows), "missing": missing}
def rate(sel, field):
    v = [r[field] for r in sel if r[field] is not None]; k = sum(v); return {"k": k, "n": len(v), "rate": round(k/len(v), 3) if v else None, "ci95": wilson(k, len(v))}
groups = ["hand_mild_decoy", "selfscreen_mild_decoy", "llm_decoy", "hand_attack", "llm_attack", "honest"]
out["by_group"] = {g: {"human": rate([r for r in rows if r["group"] == g], "human"),
                       "llm": rate([r for r in rows if r["group"] == g], "llm")} for g in groups}
dec = [r for r in rows if r["kind"] == "decoy"]; att = [r for r in rows if r["kind"] == "attack"]
out["decoys_all"] = {"human": rate(dec, "human"), "llm": rate(dec, "llm")}
out["attacks_all"] = {"human": rate(att, "human"), "llm": rate(att, "llm")}
both = [r for r in rows if r["human"] is not None and r["llm"] is not None]
a = sum(r["human"] == r["llm"] for r in both) / len(both)
p1 = sum(r["human"] for r in both) / len(both); p2 = sum(r["llm"] for r in both) / len(both)
pe = p1*p2 + (1-p1)*(1-p2); kappa = (a - pe) / (1 - pe) if pe < 1 else None
out["agreement"] = {"n": len(both), "percent": round(100*a, 1), "kappa": round(kappa, 3) if kappa is not None else None}
out["disagreements"] = [{k: r[k] for k in ("code", "group", "llm", "human", "harmful", "deceptive", "note")} for r in both if r["human"] != r["llm"]]
ts = sorted(datetime.fromisoformat(r["t"].replace("Z", "+00:00")) for r in rows if r["t"])
out["time_span_minutes"] = round((ts[-1] - ts[0]).total_seconds() / 60, 1) if ts else None
out["notes_written"] = sum(bool(r["note"]) for r in rows)
json.dump({"summary": out, "rows": rows}, open("results.json", "w"), indent=1)
print(json.dumps(out, indent=1))
