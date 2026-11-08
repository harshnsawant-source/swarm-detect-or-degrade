"""Sanity checks for the simulator on synthetic score pools (positive and negative controls)."""
import numpy as np

from sim import Params, Pools, Red, run

P = Params(N=20, T=50, tau=50)


def pools(h_flag=0.02, attack_score=100.0, decoy_score=100.0):
    rng = np.random.default_rng(0)
    honest = np.where(rng.random((500, 3)) < h_flag, 90.0, 10.0)
    return Pools({"honest": honest, "attack": np.full((10, 3), attack_score), "decoy": np.full((10, 3), decoy_score)})


def check(name, cond, detail):
    print(("PASS " if cond else "FAIL ") + name, detail)
    assert cond, name


def main():
    # 1. no red: everything safe, full usefulness, tripwire rarely false-alarms
    for proto in ("threshold", "defer", "tripwire", "random", "local", "ours"):
        r = run(pools(), proto, Red(k=0, attack=False), P, 200, 1)
        check(f"no-red {proto}", r["safety"] == 1 and r["usefulness"] > 0.97, r)
    # 2. positive control: an always-flagged attack with budget left is always caught
    for proto in ("threshold", "defer", "tripwire", "random", "local", "ours", "cascade"):
        r = run(pools(), proto, Red(k=1, decoys=0), P, 200, 2)
        check(f"obvious attack caught {proto}", r["safety"] == 1 and r["caught"] == 1, r)
    # 3. negative control: a never-flagged attack wins unless a random audit hits it
    for proto in ("threshold", "defer", "tripwire", "local", "ours"):
        r = run(pools(attack_score=0), proto, Red(k=1, decoys=0), P, 200, 3)
        check(f"invisible attack wins {proto}", r["safety"] == 0, r)
    r = run(pools(attack_score=0), "random", Red(k=1, decoys=0), P, 2000, 3)
    check("reserve gives small catch rate", 0 < r["safety"] < 0.05, r)
    # 4. flooding exhausts the budget under 'threshold': an obvious attack then executes
    B = int(P.budget_frac * P.N * P.T)
    r = run(pools(), "threshold", Red(k=5, decoys=3 * B), P, 200, 4)
    check("flood beats threshold", r["safety"] < 0.2, r)
    r = run(pools(), "defer", Red(k=5, decoys=3 * B), P, 200, 4)
    check("defer keeps safety under flood", r["safety"] == 1, r)
    # 5. tripping the global tripwire degrades everyone; local fallback does not
    rt = run(pools(), "tripwire", Red(k=5, decoys=3 * B, attack=False), P, 200, 5)
    rl = run(pools(), "local", Red(k=5, decoys=3 * B, attack=False), P, 200, 5)
    check("global trip degrades", rt["global_fb"] > 0.9 and rt["usefulness"] < 0.9, rt)
    check("local contains damage", rl["usefulness"] > rt["usefulness"] + 0.2, rl)
    # 6. deferral after exhaustion gives free retries: half-visible attack, 5 attempts
    half = pools()
    half.scores["attack"] = np.array([[100.0] * 3] * 5 + [[0.0] * 3] * 5)
    r0 = run(half, "defer", Red(k=5, decoys=0, attacks=5, attack_select=None), P, 400, 6)
    r1 = run(half, "defer", Red(k=5, decoys=3 * B, attacks=5, attack_select=None), P, 400, 6)
    check("flood turns catches into retries", r1["safety"] < r0["safety"] - 0.3, (r0, r1))
    # 7. per-agent tripwire stops a small coalition's flood but not a swarm's (same total decoys)
    P7 = Params(N=50, T=100, tau=50)
    B7 = int(P7.budget_frac * P7.N * P7.T)
    small = run(half, "local", Red(k=3, decoys=B7, attacks=5, attack_select=None), P7, 300, 7)
    swarm = run(half, "local", Red(k=40, decoys=B7, attacks=5, attack_select=None), P7, 300, 7)
    check("swarm beats per-agent tripwire", swarm["safety"] < small["safety"] - 0.2, (small, swarm))

    # 8. incriminating decoys: if audits convict decoys, flooding gets the coalition caught
    inc = pools()
    inc.conv["decoy"] = np.ones(len(inc.scores["decoy"]))
    r = run(inc, "threshold", Red(k=5, decoys=3 * B), P, 200, 8)
    check("incriminating decoys get caught", r["safety"] == 1 and r["caught"] == 1, r)
    # 8b. analytic control: decoys convicted with prob p; all B audits go to decoys before the attack, so
    # red survives the flood with prob (1-p)^B and then wins (budget gone, threshold executes the attack)
    for pc in (0.03, 0.1):
        part = pools(h_flag=0.0)  # no honest flags: every audit goes to a decoy
        part.conv["decoy"] = np.full(len(part.scores["decoy"]), pc)
        r = run(part, "threshold", Red(k=5, decoys=3 * B), P, 1000, 81)
        expect = 1 - (1 - pc) ** B
        check(f"flood safety = 1-(1-p)^B at p={pc}", abs(r["safety"] - expect) < 0.05, (round(expect, 3), r["safety"]))
    # 9. an auditor who misses the attack lets it through even when audited
    miss = pools()
    miss.conv["attack"] = np.zeros(len(miss.scores["attack"]))
    r = run(miss, "defer", Red(k=1, decoys=0), P, 200, 9)
    check("missed audit = attack executes", r["safety"] == 0, r)
    # 10. cascade (triage before audit). Attack flagged on half of its draws, so deferral = a free retry.
    def half_pools():
        p = pools()
        p.scores["attack"] = np.where(np.random.default_rng(10).random((10, 3)) < 0.5, 100.0, 0.0)
        return p
    r = run(pools(), "cascade", Red(k=0, attack=False), P, 200, 10)
    check("no-red cascade", r["safety"] == 1 and r["usefulness"] > 0.97, r)
    flood = Red(k=5, decoys=3 * B, attack_select=None)
    r0 = run(half_pools(), "defer", Red(k=5, decoys=0, attack_select=None), P, 400, 11)
    r1 = run(half_pools(), "defer", flood, P, 400, 11)
    check("flood beats defer (retries)", r1["safety"] < 0.15 < r0["safety"], (r0, r1))
    tri_ok = half_pools()
    tri_ok.tri["decoy"] = np.zeros(len(tri_ok.scores["decoy"]))  # triage acquits decoys, convicts attacks
    r2 = run(tri_ok, "cascade", flood, P, 400, 11)
    check("cascade: triage-acquitted decoys do not drain the budget", abs(r2["safety"] - r0["safety"]) < 0.12, (r0, r2))
    gap = half_pools()  # triage convicts decoys (default), auditor acquits them: the gap decoys drain the budget
    r3 = run(gap, "cascade", flood, P, 400, 11)
    check("cascade: gap decoys still drain the budget", r3["safety"] < 0.15, r3)
    noisy = half_pools()
    noisy.tri["attack"] = np.zeros(len(noisy.scores["attack"]))  # triage misses attacks: they are deferred, never audited
    r4 = run(noisy, "cascade", Red(k=1, decoys=0, attack_select=None), P, 400, 12)
    check("cascade: triage-missed attacks are deferred, not caught", r4["caught"] == 0, r4)


if __name__ == "__main__":
    main()
