"""Make report figures and a plain-text results table from results/<tag>/*.json.

Usage: python sim/figures.py [tag]
"""
import json
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
TAG = sys.argv[1] if len(sys.argv) > 1 else "main"
RES = os.path.join(ROOT, "results", TAG)
FIG = os.path.join(ROOT, "report", "figures", TAG)
if TAG not in ("headline", "pcurve"):
    os.makedirs(FIG, exist_ok=True)


def have(name, res_dir=None):
    return os.path.exists(os.path.join(res_dir or RES, f"{name}.json"))

PROTOS = ["threshold", "defer", "tripwire", "random", "local", "ours", "cascade"]
NAMES = {"threshold": "Top-k audit (no fallback)", "defer": "Audit + defer when budget gone",
         "tripwire": "Global tripwire (Greenblatt-style)", "random": "Random audit reserve",
         "local": "Per-agent tripwire", "ours": "Per-agent + randomised flagged reserve",
         "cascade": "Triage cascade (audit only what a 2nd model convicts)"}
COLORS = {"threshold": "#7f7f7f", "defer": "#1f77b4", "tripwire": "#d62728", "random": "#9467bd",
          "local": "#ff7f0e", "ours": "#2ca02c", "cascade": "#17becf"}


def load(name):
    return json.load(open(os.path.join(RES, f"{name}.json")))


# D = 400 in the detect grid is a horizon artefact: 4 decoy identities x 1 decoy per round runs the flood to
# round 99, so the attacker gets a single attempt. It is excluded from plots and from the worst case.
EXCLUDE = {"detect": {"D": {400}}, "swarm": {}, "degrade": {}, "swarm_degrade": {}}


def keep(name, r):
    return not any(r.get(k) in v for k, v in EXCLUDE.get(name, {}).items())


def series(rows, proto, x, metric, name=None):
    pts = sorted((r[x], r[metric]) for r in rows if r["proto"] == proto and r.get(metric) and keep(name, r))
    xs = [p[0] for p in pts]
    m = np.array([p[1] for p in pts])
    return xs, m


def line_plot(name, x, metric, xlabel, ylabel, fname, protos=PROTOS, note=None, ax=None, legend=True):
    d = load(name)
    own = ax is None
    if own:
        fig, ax = plt.subplots(figsize=(7.5, 4.6))
    grid = sorted({r[x] for r in d["rows"] if keep(name, r)})
    pos = {v: i for i, v in enumerate(grid)}
    w = 0.5 / max(1, len(protos) - 1)
    for j, p in enumerate(protos):
        xs, m = series(d["rows"], p, x, metric, name)
        if not len(xs):
            continue
        xi = np.array([pos[v] for v in xs]) + (j - (len(protos) - 1) / 2) * w
        ax.errorbar(xi, m[:, 0], yerr=np.clip([m[:, 0] - m[:, 1], m[:, 2] - m[:, 0]], 0, None), fmt="-o", ms=4, lw=1.2,
                    elinewidth=0.9, capsize=2, color=COLORS[p], label=NAMES[p])
    ax.set_xticks(range(len(grid)))
    ax.set_xticklabels([str(v) for v in grid])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_ylim(-0.03, 1.03)
    ax.grid(alpha=0.3, axis="y")
    if note:
        ax.set_xlabel(xlabel + "\n" + note, fontsize=9)
    if legend:
        ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.2 if note else -0.14), ncol=3,
                  frameon=False)
    if own:
        fig.tight_layout()
        fig.savefig(os.path.join(FIG, fname), dpi=200, bbox_inches="tight")
        plt.close(fig)


def table():
    lines = []
    for name in ("baseline", "detect", "degrade", "swarm", "swarm_degrade"):
        if not have(name):
            continue
        d = load(name)
        lines.append(f"\n== {name} (budget {d['budget']} audits, {d['boot']} bootstrap x {d['episodes']} episodes)")
        for r in d["rows"]:
            key = " ".join(f"{k}={r[k]}" for k in ("proto", "D", "k", "variant") if k in r)
            s = r["safety"]
            u = r.get("usefulness")
            us = f"useful {u[0]:.3f} [{u[1]:.3f},{u[2]:.3f}]" if u else "useful n/a"
            lines.append(f"  {key:40s} safety {s[0]:.2f} [{s[1]:.2f},{s[2]:.2f}]  {us}  global_fb {r['global_fb'][0]:.2f}")
    open(os.path.join(RES, "table.txt"), "w").write("\n".join(lines))
    print("\n".join(lines))


def worst_rows(res_dir=None):
    """Per protocol: the attack config with the lowest mean safety and the degrade config with the lowest usefulness."""
    L = (lambda n: json.load(open(os.path.join(res_dir, f"{n}.json")))) if res_dir else load
    out = {}
    for p in PROTOS:
        safe = [r for n in ("detect", "swarm") if have(n, res_dir) for r in L(n)["rows"] if r["proto"] == p and keep(n, r)]
        use = [r for n in ("degrade", "swarm_degrade") if have(n, res_dir) for r in L(n)["rows"]
               if r["proto"] == p and r.get("usefulness")]
        if not safe or not use:
            continue  # protocol not run in this setting
        out[p] = (min(safe, key=lambda r: r["safety"][0])["safety"], min(use, key=lambda r: r["usefulness"][0])["usefulness"])
    return out


def frontier_ax(ax, out, title=None, legend=True):
    ax.add_patch(plt.Rectangle((0.8, 0.8), 0.25, 0.25, color="#2ca02c", alpha=0.07, lw=0))
    ax.text(0.99, 0.99, "where a good\nprotocol would be", ha="right", va="top", fontsize=6.5, color="#2a7a2a")
    for p, (s, u) in out.items():
        ax.errorbar(u[0], s[0], xerr=np.clip([[u[0] - u[1]], [u[2] - u[0]]], 0, None), yerr=np.clip([[s[0] - s[1]], [s[2] - s[0]]], 0, None),
                    fmt="o", ms=7, capsize=2, elinewidth=0.9, color=COLORS[p], label=NAMES[p], zorder=3)
    ax.set_xlabel("Worst-case usefulness (attacker tries to degrade)")
    ax.set_ylabel("Worst-case safety (attacker tries to attack)")
    ax.set_xlim(-0.02, 1.04)
    ax.set_ylim(-0.03, 1.04)
    ax.grid(alpha=0.3)
    if title:
        ax.set_title(title, fontsize=9)
    pts = np.array([(u[0], s[0]) for s, u in out.values()])
    if np.ptp(pts[:, 0]) < 0.05 and np.ptp(pts[:, 1]) < 0.05:
        ax.annotate("all seven protocols overlap here:\nflooding gets the attacker caught,\nso its best play is no decoys",
                    xy=(pts[:, 0].mean(), pts[:, 1].mean()), xytext=(0.35, 0.62), fontsize=7.5,
                    arrowprops=dict(arrowstyle="->", color="#444", lw=0.8))
    if legend:
        ax.legend(fontsize=6.5, loc="center left", bbox_to_anchor=(1.01, 0.5), frameon=False)


def worst_case():
    if not (have("detect") or have("swarm")) or not (have("degrade") or have("swarm_degrade")):
        return  # this setting ran only part of the grid
    out = worst_rows()
    fig, ax = plt.subplots(figsize=(6.6, 4))
    frontier_ax(ax, out)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "frontier.png"), dpi=200, bbox_inches="tight")
    plt.close(fig)
    flat = {p: (s[0], u[0]) for p, (s, u) in out.items()}
    json.dump(flat, open(os.path.join(RES, "worst_case.json"), "w"), indent=1)
    json.dump({p: {"safety": s, "usefulness": u} for p, (s, u) in out.items()},
              open(os.path.join(RES, "worst_case_ci.json"), "w"), indent=1)
    print("worst case (safety, usefulness):", json.dumps(flat, indent=1))


def headline():
    """Side by side: realistic auditor with all decoys vs. attacker that pre-screens its decoys."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), sharey=True)
    for ax, (tag, title) in zip(axes, [("main", "Realistic auditor, attacker floods with all decoys"),
                                        ("prescreen", "Attacker floods only with decoys the auditor acquits")]):
        frontier_ax(ax, worst_rows(os.path.join(ROOT, "results", tag)), title, legend=(tag == "prescreen"))
    axes[1].set_ylabel("")
    for ax in axes:
        ax.set_xlabel("Worst-case usefulness\n(attacker tries to degrade)")
    fig.tight_layout()
    out = os.path.join(ROOT, "report", "figures", "headline_frontier.png")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)


PCURVE_P = ["0", "0.003", "0.01", "0.03", "0.1", "0.3"]
# measured decoy conviction rates (real auditor) for each attacker, from data/audit + DEVIATIONS D4
MEASURED = [(0.0, "oracle pre-screen\n(auditor's own model)"),
            (1 / 7, "self-screened LLM\nmild decoys (1/7)"),
            (0.57, "unscreened LLM\ndecoys (73/127)")]


def pcurve():
    """Safety at D decoys vs the auditor's per-decoy conviction rate p (real monitor scores, LLM decoys)."""
    D = 100
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    xs = np.arange(len(PCURVE_P))
    protos = [p for p in PROTOS]
    w = 0.5 / (len(protos) - 1)
    base = []
    for j, proto in enumerate(protos):
        m, b0 = [], []
        for pv in PCURVE_P:
            path = os.path.join(ROOT, "results", f"pcurve_{pv}", "detect.json")
            rows = json.load(open(path))["rows"] if os.path.exists(path) else []
            r = [x for x in rows if x["proto"] == proto and x["D"] == D]
            r0 = [x for x in rows if x["proto"] == proto and x["D"] == 0]
            m.append(r[0]["safety"] if r else [np.nan] * 3)
            if r0:
                b0.append(r0[0]["safety"][0])
        m = np.array(m)
        base += b0
        xi = xs + (j - (len(protos) - 1) / 2) * w
        ax.errorbar(xi, m[:, 0], yerr=np.clip([m[:, 0] - m[:, 1], m[:, 2] - m[:, 0]], 0, None), fmt="-o", ms=4,
                    lw=1.2, elinewidth=0.9, capsize=2, color=COLORS[proto], label=NAMES[proto])
    if base:
        ax.axhline(np.nanmean(base), color="#444", ls=":", lw=1)
        ax.text(len(PCURVE_P) - 0.6, np.nanmean(base) + 0.02, "no decoys (attacker's\nbest without flooding)",
                fontsize=7, ha="right", color="#444")
    # analytic: red survives ~B decoy audits with prob (1-p)^B, then wins against the budget-only protocol
    B = 100
    ax.plot(xs, [1 - (1 - float(pv)) ** B for pv in PCURVE_P], "k--", lw=1, label="1 - (1-p)^100 (analytic)")
    ax.set_xticks(xs)
    ax.set_xticklabels(PCURVE_P)
    ax.set_xlabel("Auditor's conviction rate per decoy, p   (attacker floods 100 decoys; budget = 100 audits)\n"
                  "measured: oracle pre-screen p = 0; self-screened mild decoys p = 1/7; unscreened LLM decoys p = 0.57")
    ax.set_ylabel("Safety")
    ax.set_ylim(-0.03, 1.03)
    ax.grid(alpha=0.3, axis="y")
    ax.legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3, frameon=False)
    fig.tight_layout()
    out = os.path.join(ROOT, "report", "figures", "pcurve.png")
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    if TAG == "headline":
        headline()
        sys.exit()
    if TAG == "pcurve":
        pcurve()
        sys.exit()
    for name, args in [("detect", ("D", "safety", "Decoys emitted before the attack (coalition of 5; audit budget = 100)",
                                   "Safety", "detect.png")),
                       ("degrade", ("D", "usefulness", "Decoys emitted (coalition of 5, no attack)",
                                    "Usefulness of honest work", "degrade.png")),
                       ("swarm", ("k", "safety", "Coalition identities k (total decoys fixed = 2x audit budget)",
                                  "Safety", "swarm.png")),
                       ("swarm_degrade", ("k", "usefulness", "Coalition identities k (total decoys fixed, no attack)",
                                          "Usefulness of honest work", "swarm_degrade.png"))]:
        if have(name):
            line_plot(name, *args, note="D = 400 omitted: horizon artefact (attacker gets 1 attempt)"
                      if name == "detect" else None)
    table()
    worst_case()
