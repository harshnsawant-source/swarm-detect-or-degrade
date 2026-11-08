"""data/items_v3.jsonl = data/items_v2.jsonl + verified mild decoys from data/gen/mild.jsonl (deviation D4).

Mild decoys get kind 'decoy', source 'mild', ids '<template>:gen-mild-<sample>'. Exact duplicate code within a
template is dropped. items_v2 is left unchanged, so every earlier result stays reproducible.
"""
import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "tasks"))
from templates_1 import T as T1  # noqa: E402
from templates_2 import T as T2  # noqa: E402

desc = {t["id"]: t["desc"] for t in T1 + T2}
rows = [json.loads(l) for l in open(os.path.join(ROOT, "data", "items_v2.jsonl"), encoding="utf-8")]
seen, n, kept = set(), 0, 0
for l in open(os.path.join(ROOT, "data", "gen", "mild.jsonl"), encoding="utf-8"):
    g = json.loads(l)
    n += 1
    key = (g["template"], g["code"].strip())
    if not g["verified"] or key in seen:
        continue
    seen.add(key)
    kept += 1
    rows.append(dict(item_id=f"{g['template']}:gen-mild-{g['sample']}", template=g["template"], kind="decoy",
                     label="gen-mild", desc=desc[g["template"]], code=g["code"], lines_changed=None,
                     verified=True, source="mild"))
with open(os.path.join(ROOT, "data", "items_v3.jsonl"), "w", encoding="utf-8") as f:
    for r in rows:
        f.write(json.dumps(r) + "\n")
print(f"mild: {n} samples, {kept} verified and kept; items_v3: {len(rows)} items")
