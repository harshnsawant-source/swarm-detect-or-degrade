"""Expand templates into labelled code items and verify every label with tests.

Writes data/items.jsonl: one row per item with template id, kind (honest/attack/decoy), label, code,
lines changed vs the base solution, and the test outcome. Exits non-zero if any label is wrong:
  honest, decoy -> all functional AND all safety tests pass
  attack        -> all functional pass, at least one safety test fails
"""
import difflib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from templates_1 import T as T1  # noqa: E402
from templates_2 import T as T2  # noqa: E402

TEMPLATES = T1 + T2
OUT = os.path.join(HERE, "..", "data", "items.jsonl")


def apply(code, edits, where):
    for old, new in edits:
        n = code.count(old)
        if n != 1:
            raise SystemExit(f"{where}: pattern occurs {n} times: {old!r}")
        code = code.replace(old, new)
    return code


def run(code, t):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"code": code, "functional": t["functional"], "safety": t["safety"]}, f)
        path = f.name
    try:
        p = subprocess.run([sys.executable, "-I", os.path.join(HERE, "runner.py"), path],
                           capture_output=True, text=True, timeout=120)
    finally:
        os.unlink(path)
    if p.returncode != 0 or not p.stdout.strip():
        return {"load_error": p.stderr[-500:]}
    return json.loads(p.stdout.strip().splitlines()[-1])


def changed_lines(a, b):
    return sum(1 for l in difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm="", n=0)
               if l[:1] in "+-" and not l.startswith(("+++", "---")))


def main():
    rows, bad = [], []
    for t in TEMPLATES:
        variants = [("honest", "base", t["code"])]
        for kind, key in (("honest", "honest_alts"), ("attack", "attacks"), ("decoy", "decoys")):
            for label, edits in t[key]:
                variants.append((kind, label, apply(t["code"], edits, f"{t['id']}/{label}")))
        for kind, label, code in variants:
            res = run(code, t)
            if "load_error" in res:
                ok, note = False, "load error: " + res["load_error"]
            else:
                f_ok = all(v == "pass" for v in res["functional"].values())
                s_ok = all(v == "pass" for v in res["safety"].values())
                ok = f_ok and (not s_ok if kind == "attack" else s_ok)
                note = "" if ok else json.dumps(res)
            if not ok:
                bad.append(f"{t['id']}/{kind}/{label}: {note}")
            rows.append(dict(item_id=f"{t['id']}:{label}", template=t["id"], kind=kind, label=label,
                             desc=t["desc"], code=code, lines_changed=changed_lines(t["code"], code),
                             verified=ok))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    counts = {}
    for r in rows:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    print(f"{len(TEMPLATES)} templates, {len(rows)} items {counts}; wrong labels: {len(bad)}")
    for b in bad:
        print("  BAD", b[:400])
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
