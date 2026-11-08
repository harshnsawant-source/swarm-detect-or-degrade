"""Merge hand-written items (data/items.jsonl) and verified generated items (data/gen/*.jsonl)
into data/items_v2.jsonl. Generated items get ids '<template>:gen-<kind>-<sample>' and source 'llm'.
Duplicate generated code within a template+kind is dropped."""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "tasks"))
from templates_1 import T as T1  # noqa: E402
from templates_2 import T as T2  # noqa: E402

desc = {t["id"]: t["desc"] for t in T1 + T2}
rows = []
for l in open(os.path.join(ROOT, "data", "items.jsonl"), encoding="utf-8"):
    r = json.loads(l)
    r["source"] = "hand"
    rows.append(r)
stats = {}
for kind in ("honest", "decoy", "attack"):
    path = os.path.join(ROOT, "data", "gen", f"{kind}.jsonl")
    if not os.path.exists(path):
        continue
    seen = set()
    for l in open(path, encoding="utf-8"):
        g = json.loads(l)
        key = (g["template"], g["code"].strip())
        st = stats.setdefault(kind, {"samples": 0, "verified": 0, "kept": 0})
        st["samples"] += 1
        if not g["verified"]:
            continue
        st["verified"] += 1
        if key in seen:
            continue
        seen.add(key)
        st["kept"] += 1
        rows.append(dict(item_id=f"{g['template']}:gen-{kind}-{g['sample']}", template=g["template"], kind=kind,
                         label=f"gen-{kind}", desc=desc[g["template"]], code=g["code"], lines_changed=None,
                         verified=True, source="llm"))
with open(os.path.join(ROOT, "data", "items_v2.jsonl"), "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
print(len(rows), "items;", json.dumps(stats))
