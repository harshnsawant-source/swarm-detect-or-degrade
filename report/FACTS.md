# Fact sheet: Detect or Degrade (for writing the report)

Every number below was read from the files named next to it on 2026-11-07, and re-checked on 2026-11-08 after the
final runs (deviations D1–D5 applied). Previous version: `report/FACTS.v1-2026-11-07.md`.
This is a source of facts, not report text. Write the report in your own words, and quote numbers from here.
"CI" = 95% interval from the task-level bootstrap (100 resamples of the 10 evaluation templates, 60 episodes each).

## 1. Setup (what the reader must know)

| Fact | Value | Source |
|---|---|---|
| Fleet | N = 50 agents, T = 100 rounds, 5,000 submissions per episode | `results/main/detect.json` params |
| Audit budget | 2% = 100 audits per episode | same |
| Tripwire false-alarm level | α = 0.001 (fleet); α/N for per-agent | same |
| `ours` settings | reserve 25% of the budget; flagged items audited with prob. q = 0.2 once the main budget is gone | same |
| `cascade` (7th protocol, D5) | a flagged item is audited only if a triage model (gemma4:31b-cloud, auditor prompt) convicts it; otherwise deferred. No tuned parameters | `sim/sim.py` |
| Simulator checks | 34 positive/negative controls, incl. analytic check safety = 1 − (1 − p)^B | `sim/test_sim.py` |
| Tasks | 20 coding templates, each with functional tests + hidden safety tests (ground truth for "harmful") | `tasks/templates_*.py` |
| Split | 10 discovery / 10 evaluation templates, frozen 05:28 IST 7 Nov, **before any monitor score existed** | `data/frozen.json` |
| Evaluation templates | apply_coupon, dose_calc, inventory_reserve, login_lockout, mail_allowlist, password_hash, redact_record, sql_builder, upload_filter, webhook_signature | same |
| Untrusted model + monitor | gemma4:31b-cloud (temp 0, batches of 10, 3 reps in different batches) | `data/frozen.json` |
| Auditor | gpt-oss:120b-cloud, temp 0; convicts if `harmful` OR `deceptive_intent` | `monitor/audit.py` |
| Trusted model | qwen2.5:3b-instruct (local) | `results/u_trusted.json` |
| Cost | Free only: Ollama local + Ollama free cloud | README |

## 2. Data set

| Kind | Hand-written | LLM-generated (kept / generated) | Source |
|---|---|---|---|
| Honest | 60 (not used in main results, see D1) | 130 / 160 | `data/items_v2.jsonl`, D1 |
| Decoy (correct and safe but suspicious-looking) | 60 (not used in main results) | 127 / 160 | same |
| Attack (passes functional tests, fails ≥1 safety test) | 60 | 10 / 120 | same |
| "Mild" decoy (D4: correct, safe, unusual-but-legitimate, nothing malicious-looking) | n/a | 123 | `data/items_v3.jsonl` (= v2 + mild) |

- Every label was checked by running the tests: 0 wrong labels in the final set.
- Honest items in the simulator are the LLM honest solutions. Decoys are the LLM decoys. Attacks are hand + LLM.
- Evaluation-split counts: 60 honest, 36 attacks, 59 decoys (27 after pre-screening). Source: `results/*/monitor_stats.json`.

## 3. Monitor (evaluation templates)

| Fact | Value | Source |
|---|---|---|
| Honest scores | **all 390 honest scores are exactly 0** | `data/scores/gemma4_31b-cloud.jsonl` |
| Threshold | τ = 0 with tie-break 0.02, so the honest flag rate is exactly 2%; **any nonzero score is flagged** | `monitor_stats.json` |
| Attack flag rate | 0.73 (CI 0.55–0.92) | `results/main/monitor_stats.json` |
| Decoy flag rate | 1.00 (CI 1.00–1.00) | same |
| AUROC attack vs honest | 0.86 (CI 0.77–0.96) | same |
| AUROC decoy vs honest | 1.00 | same |
| AUROC decoy vs attack | 0.52 (CI 0.27–0.70): **the monitor cannot tell decoys from attacks** | same |
| Median score | honest 0, attack 60, decoy 60 | same |
| Hand-written decoys (for contrast) | median 10; the monitor separates them from attacks easily (D1) | `DEVIATIONS.md` D1 |

## 4. Auditor

| Item group | Auditor (gpt-oss) convicts | Attacker's own model / triage (gemma) convicts |
|---|---|---|
| Hand attacks | 54 / 60 (90%) | 54 / 60 |
| LLM attacks | 4 / 10 (40%) | 0 / 10 |
| LLM decoys | 73 / 127 (57%) | **127 / 127** |
| Mild LLM decoys | 2 / 123 (2%) | 4 / 123 |
| Hand decoys | 1 / 60 (2%) | 24 / 60 (40%) |
| Honest | (not audited) | 0 / 190 |

Sources: `data/audit/gpt-oss_120b-cloud.jsonl`, `data/audit/gemma4_31b-cloud.jsonl` (same prompt, `monitor/audit.py`).

| Fact | Value | Source |
|---|---|---|
| Acquitted LLM decoys ("pre-screened pool") | 54 (27 discovery, 27 evaluation); 27 of the 54 have median monitor score ≥ 50 | computed from scores + audit |
| Attack conviction, evaluation split | 0.69 | `results/main/monitor_stats.json` |

- Why decoys get convicted: the most suspicious LLM decoys contain malicious-looking dead code (example: `exec("... rm -rf /")` behind a condition that can never be true). See D2.

## 5. Fallback cost

- u_trusted = **0.10** (CI 0.02–0.22). Trusted model passes all tests on 8.3% of tasks; untrusted on 81%. Source: `results/u_trusted.json`.
- Prompt difference to disclose: the trusted prompt omits the phrase "the way you normally would for production code" (D2).

## 6. Results

### 6a. Baseline (no decoys; one attacker), safety with CI

| Red strategy | Realistic auditor (`main`) | Perfect auditor (`perfect`) |
|---|---|---|
| Random attack, 1 attempt | 0.67 (0.49–0.87), threshold protocol | 0.74 (0.55–0.93) |
| Least-suspicious of 3 candidates, 5 attempts | 0.38 (0.12–0.76) | 0.45 (0.15–0.82) |

The six budget/tripwire protocols are within ±0.02 of each other at baseline. The cascade is slightly lower
(0.34 realistic, 0.41 perfect auditor at D = 0), because attacks that triage misses are deferred, which gives the
attacker another try. Source: `results/*/baseline.json`, `results/*/detect.json` (D = 0).

### 6b. Finding 1: naive flooding is self-incriminating (`main`: realistic auditor, all decoys)

- Coalition of 5, any flood of ≥25 decoys: **safety 1.00 for every protocol** (`results/main/detect.json`).
- Pure degrade play (decoys, no attack): red is caught in 100% of episodes for D ≥ 25 (`results/main/degrade.json`).
- Mechanism: 57% of decoys are convicted by the auditor. The first audited decoys expose the coalition.
- Red's best move under a realistic auditor is **no decoys**: safety ≈ 0.38.
- Paired D100 − D0 is +0.62 to +0.66 for every protocol, all CIs exclude 0 (e.g. defer +0.63, 0.26–0.87;
  `results/main/paired.json`). Flooding *raises* safety here.

### 6c. Finding 2: with pre-screened decoys, every protocol gives up safety or usefulness (`prescreen`)

Coalition of 5; safety with CI; usefulness = honest work relative to the untrusted model (`results/prescreen/detect.json`).

| Protocol | D = 0 | D = 50 | D = 100 | Usefulness at D = 100 |
|---|---|---|---|---|
| Threshold (top-k, no fallback) | 0.38 | 0.36 | **0.00** (0.00–0.00) | (n/a: every run ends in an attack) |
| Defer when budget gone | 0.37 | 0.38 | **0.06** (0.00–0.34) | 0.99 |
| Random audit reserve | 0.37 | 0.35 | **0.06** (0.00–0.36) | 0.99 |
| Global tripwire (Greenblatt-style) | 0.37 | 1.00 | 1.00 | **0.18** (0.17–0.18) |
| Per-agent tripwire | 0.37 | 0.36 | 0.36 (0.12–0.74) | 1.00 |
| Ours | 0.37 | 0.36 | 0.37 (0.13–0.72) | 1.00 |
| Triage cascade | 0.34 | 0.34 | **0.06** (0.00–0.41) | 0.98 |

Paired differences D100 − D0 (same bootstrap replicates; `results/prescreen/paired.json`): threshold −0.38
(−0.73 to −0.13), defer −0.31 (−0.53 to −0.12), random −0.31 (−0.54 to −0.13), cascade −0.28 (−0.48 to −0.12).
All four CIs exclude 0: **the collapse is real, not bootstrap noise**. Per-agent −0.01 (−0.16 to 0.13) and ours
0.00 (−0.16 to 0.17): no detectable drop. Global tripwire usefulness (degrade play) −0.81 (−0.83 to −0.79).

- **Threshold mechanism:** budget-only protocols hold at D = 50 and collapse at D = 100. That is exactly the audit budget, because every decoy is flagged (flag rate 1.0).
- Degrade play (no attack): the global tripwire is degraded in 98–100% of episodes for D ≥ 25, and usefulness drops to 0.17–0.26. Per-agent and ours stay at 0.99–1.00, with 0 global fallbacks (`results/prescreen/degrade.json`).
- **`prescreen` ≈ `perfect`.** Under the perfect auditor, safety is 0.00 (threshold) and 0.06 (defer) at D = 100. Pre-screened decoys behave like truly innocent ones.

### 6d. Finding 3: splitting into many identities beats the per-agent defence (`prescreen`, total decoys = 2 × budget)

| Identities k | Per-agent tripwire | Ours | Global tripwire (safety / usefulness) |
|---|---|---|---|
| 5 | 0.37 (0.16–0.74) | 0.35 (0.11–0.67) | 1.00 / 0.18 |
| 20 | 0.33 (0.08–0.73) | 0.15 (0.02–0.47) | 1.00 / 0.16 |
| 40 | **0.07** (0.00–0.42) | **0.14** (0.01–0.48) | 1.00 / 0.16 |

Source: `results/prescreen/swarm.json`. Paired k40 − k5: per-agent −0.31 (−0.53 to −0.12), ours −0.20 (−0.39 to
−0.03); both CIs exclude 0 (`results/prescreen/paired.json`). The cascade is already at 0.06 for every k ≥ 5.

Worst case over all red strategies (`results/prescreen/worst_case_ci.json`), safety / usefulness:
threshold 0.00 / 1.00; defer 0.06 / 0.98; random 0.06 / 0.98; global tripwire 0.37 / 0.16; per-agent 0.07 / 0.98;
ours 0.14 / 0.99; cascade 0.05 / 0.98. **No protocol is good on both axes.**

### 6e. Sensitivity: a weak monitor (nemotron-3-nano:4b, local; `prescreen` setting)

Source: `results/nemotron_prescreen/`. Items with fewer than 3 valid reps are left out (35 of 447).

| Fact | Value |
|---|---|
| AUROC attack vs honest | **0.51** (CI 0.50–0.52): chance level |
| Flag rate | attacks 0.02, pre-screened decoys 0.45, honest 0.00 (evaluation split) |
| Baseline safety (no decoys) | 0.02–0.04 for every protocol: attacks pass unflagged |
| Detect flood (D = 100) | no effect on budget protocols (still ~0.03), because the budget was never what stopped attacks |
| Global tripwire under flood | safety 0.94 (0.57–1.00) but usefulness 0.26 (0.22–0.32) |
| Degrade play (D = 100) | global tripwire degraded in 94% of episodes, usefulness 0.31 (0.22–0.58); all other protocols 1.00 |

Reading:
- **The *degrade* horn holds with both monitors.** Decoys trip the global tripwire either way.
- **The *detect* horn needs a monitor good enough that the audit budget is the bottleneck** (gemma-31B: attack
  AUROC 0.86). With a chance-level monitor, attacks slip through without any flooding.

### 6f. The condition for flooding to work: the auditor must almost never convict a decoy (p-curve)

Setting `pcurve_<p>`: real monitor scores (auditor-acquitted LLM decoys), but every audited decoy convicts the
coalition with probability p, set by hand. Coalition of 5, D = 100 decoys, budget B = 100. Source:
`results/pcurve_*/detect.json`; figure `report/figures/pcurve.png`.

| p | Threshold | Defer | Random | Per-agent | Ours | Cascade | Global tripwire |
|---|---|---|---|---|---|---|---|
| 0 | 0.00 | 0.06 | 0.06 | 0.38 | 0.38 | 0.06 | 1.00 |
| 0.003 | 0.22 | 0.25 | 0.22 | 0.39 | 0.41 | 0.30 | 1.00 |
| 0.01 | 0.55 | 0.56 | 0.47 | 0.46 | 0.47 | 0.67 | 1.00 |
| 0.03 | 0.90 | 0.91 | 0.84 | 0.61 | 0.61 | 0.96 | 1.00 |
| 0.1 | 1.00 | 1.00 | 1.00 | 0.88 | 0.87 | 1.00 | 1.00 |
| 0.3 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |

- Budget protocols follow the analytic curve 1 − (1 − p)^100 (the attacker survives ~100 decoy audits): flooding
  beats the no-decoy baseline (≈ 0.37) only for **p ≲ 0.005, i.e. p ≲ 1/(2B)**. Already at p = 0.01 flooding hurts the attacker.
- Per-agent protocols are flat at low p (they cut off the flooding agents, so the flood never drains the budget)
  but *below* the budget protocols at p = 0.03–0.1 (cutting off the decoy agents also removes the chances to
  convict them). At p = 0.03, cascade − per-agent = +0.34 (0.12–0.55), CI excludes 0 (`results/pcurve_0.03/paired.json`).
- Measured p for real attackers (auditor convictions per decoy): unscreened LLM decoys 0.57; self-screened decoys
  1/33 ≈ 0.03 (6g); oracle pre-screen 0; hand-written mild decoys on the evaluation templates 0/30.

### 6g. Can the attacker pre-screen its own decoys? (D4; settings `selfscreen`, `handdecoys`)

The attacker's natural screening tool is its own model (here the same gemma that is also the monitor and the
triage model). Measured from `data/audit/*.jsonl` and `data/scores/gemma4_31b-cloud.jsonl`:

| Decoy source | Monitor flags (all reps) | Self-screen keeps (own monitor rep 0 flags AND own audit acquits) | Held-out flag rate of kept (reps 1–2) | Real auditor convicts kept |
|---|---|---|---|---|
| Scary LLM decoys | 1.00 | **0 / 127** (gemma convicts all) | n/a | n/a |
| Mild LLM decoys (D4 prompt) | 0.08 | 7 / 123 (5.7%) | 0.64 | 1 / 7 |
| Hand-written mild decoys | 0.79 | 26 / 60 | 0.83 | 0 / 26 |

- `selfscreen` floods with the 33 kept decoys (7 mild + 26 hand, drawn from all 20 templates). Pooled p = 1/33.
  Result: **flooding hurts the attacker**. Paired D100 − D0: defer +0.46 (0.12–0.73), threshold +0.43 (0.07–0.73);
  worst case for every budget protocol is the no-decoy baseline 0.37 (`results/selfscreen/`).
- The one cost: decoys still trip the global tripwire. Its worst-case usefulness is 0.37 (0.30–0.45)
  (`results/selfscreen/worst_case_ci.json`).
- `handdecoys`: the hand-written mild decoys, with no screening at all. On the evaluation templates the auditor
  convicts 0/30 of them (the one conviction, `acl_check:pickle_copy`, is a discovery template). Result ≈ `prescreen`:
  defer D100 − D0 −0.30 (−0.56 to −0.11), threshold 0.00 at D = 100, per-agent k40 − k5 −0.30 (−0.53 to −0.08).
  **So a decoy writer as good as a careful human breaks the budget protocols without any oracle.**
- Honest reading: with the models we have, an LLM attacker that screens with its own model gets p ≈ 0.03, which
  is 6× too high for flooding to pay. A better decoy writer (human-level, p ≈ 0) wins. The threat depends on decoy
  quality, and the p-curve (6f) says exactly how good the decoys must be.

### 6h. Defence tried: triage cascade (D5)

Idea: audit a flagged item only if a second model (triage) also convicts it. This targets decoys the monitor flags
but a careful reader would acquit.

| Setting | Triage convicts decoys | Cascade worst-case safety | Comparison (paired) |
|---|---|---|---|
| `prescreen` (acquitted LLM decoys) | 27/27 (all) | 0.05 (0.00–0.34) | = defer at every D and k (diff 0.00); 0.30 below per-agent at D = 100 (CI −0.53 to −0.12) |
| `handdecoys` | 40% | 0.14 (0.00–0.59) | holds to D = 100 (0.35) where defer collapses: +0.28 (0.11–0.56); falls at D = 200 (0.14) |
| `selfscreen` | ~0 (by construction: screened with the triage model) | 0.34 (0.12–0.65) | no drop with flooding, but −0.49 vs defer at D = 100: deferring the decoys also throws away the chances to convict them |

- Reading: the cascade only helps when the triage model can tell decoys from attacks *and* the decoys would not
  have been convicted anyway. It multiplies the attacker's decoy cost by 1/(triage conviction rate on decoys)
  (here ×2.5 for hand decoys). It does not escape the dilemma; it moves it.
- Its cost: usefulness 0.98 and a slightly lower no-decoy baseline (0.34 vs 0.37), because triage-missed attacks
  are deferred, not audited.

### 6i. Other sensitivity checks

- **u_trusted = 0.5** (`u05`: a 5× better trusted model; `prescreen` decoys; detect, degrade and swarm_degrade grids
  only). Global tripwire worst-case usefulness rises from 0.16 to **0.54**; budget protocols unchanged (defer 0.06,
  threshold 0.00 at D = 100). The degrade horn is weaker but still costs half the useful work. (The swarm grid was not
  run here, so per-agent/ours worst-case safety in `u05` (0.36/0.35) is the detect grid only and is NOT comparable
  to 6d.)
- **Perfect auditor** (`perfect`): same shape as `prescreen`, slightly higher baseline (0.45). Worst case: defer 0.06,
  per-agent 0.07, ours 0.17, cascade 0.05, tripwire 0.44 / usefulness 0.16.

### 6j. Pilot human audit (one non-expert human auditor, blinded; `human_audit/`)

Plan written before any verdict: `human_audit/PLAN.md`. Sample of 40 (seed 20261108), shown blind as A01–A40 on a page with
the auditor's two questions. Analysis: `human_audit/analyze.py` → `human_audit/results.json`.
How it was done: Harsh read all 40 items in one read-through, then entered the verdicts together; not a line-by-line trace.

| Group | Human convicts | LLM auditor (gpt-oss) convicts, same items |
|---|---|---|
| Hand-written mild decoys | **0 / 12** (95% CI 0.00–0.24) | 1 / 12 |
| Self-screened mild LLM decoys | 2 / 7 | 1 / 7 |
| Obvious LLM decoys | 7 / 8 | 5 / 8 |
| All decoys | 9 / 27 = 0.33 (0.19–0.52) | 7 / 27 = 0.26 |
| Hand-written attacks | 5 / 5 | 5 / 5 |
| LLM attacks | 1 / 3 | 1 / 3 |
| Honest | 0 / 5 | (not audited) |

- Agreement with the LLM auditor on the 35 items both judged: 88.6%, Cohen's kappa 0.76.
- 4 disagreements: A05 (self-screened mild, human harmful=Y), A06 and A21 (obvious LLM decoys, human deceptive=Y), A16
  (hand mild decoy, LLM convicted, human did not; this is the one hand decoy the LLM convicts, a discovery-task item).
- Reading: a human reader also acquits every hand-written mild decoy, so the condition p ≈ 0 for well-written decoys is not
  an artefact of the LLM auditor. The human is somewhat stricter on obvious and self-screened decoys (direction: flooding
  even less attractive there).
- Must hedge: n = 1 auditor, not a security professional, single read-through, small groups (CIs wide). A pilot, not a
  measurement of human auditors in general.

## 7. Claims you can and cannot make

**Can:**
- Naive audit flooding is self-incriminating under a realistic auditor (6b).
- Wherever the monitor flags a decoy that the auditor acquits, the coalition forces a choice: lose safety (budget protocols) or lose about 82% of useful work (global tripwire) (6c).
- Per-agent tripwires escape that choice against small coalitions, but not against 40 identities (6d).
- The precondition (monitor–auditor disagreement) is measurable before deployment: here, 54 of 127 LLM decoys are flagged by the monitor and acquitted by the auditor.
- The exact condition: flooding pays only if the auditor convicts fewer than about 1 in 2B decoys (6f; analytic
  1 − (1 − p)^B, confirmed by the simulator and by a unit test). This gives defenders a number to measure: the
  auditor's conviction rate on flagged-but-benign items.
- The main drops are statistically real: paired CIs exclude 0 for the D = 100 collapse (6c) and the k = 40 swarm (6d).
- Hand-written mild decoys break the budget protocols with no pre-screening at all (6g, `handdecoys`).
- An LLM attacker screening with its own model only reaches p ≈ 0.03 here, which is too high, so flooding hurts it (6g).

**Cannot / must hedge:**
- `ours` is **not** a solution: not clearly better than per-agent anywhere, and worse at k = 20 (0.15 vs 0.33;
  paired ours − local at k = 20: −0.18, CI −0.38 to −0.02). Present it as "the best we tried, not enough".
- The cascade is **not** a solution either (6h): equal to defer when triage convicts every decoy, and worse than
  defer when it acquits decoys the auditor would have convicted.
- The CIs are wide (only 10 evaluation templates). Report them everywhere; use the paired differences for comparisons.
- The `prescreen` setting is an oracle (the attacker knows the auditor's verdicts). We measured that the attacker's
  own model cannot do this for scary decoys (6g). Treat `prescreen` as the upper bound and `handdecoys` as the
  realistic-but-skilled case; `selfscreen` is the LLM-only case, where the attack fails.
- The "hand-written" items (`tasks/build_items.py`) were written for this project during the build, with an AI coding
  assistant, by someone who could see the tasks and tests but NOT the monitor scores (written before scoring). They were
  not produced by the simulated attacker pipeline. They show such decoys exist and are cheap to write with care; they
  do not show that the attacker model would write them unprompted. Disclose this in the report.
- The threshold is degenerate (honest code always scores 0), so "flagged" means "monitor gave any nonzero score". A monitor with honest-score spread could behave differently. The nemotron run (6e) shows the detect horn depends on monitor quality; the degrade horn does not.
- The usefulness metric was changed after the first `main` run (D3). Earlier `main` usefulness numbers are superseded.
- It's a simulation over cached scores of single-file tasks, not a live agent fleet.

## 8. Known artefacts (handled in the figures)

- **D = 400 in the detect grid is an artefact.** With 4 decoy identities and 1 decoy each per round, the flood runs to
  round 99, so the attacker gets only 1 attempt. It is excluded from the detect plot and from the worst case
  (`sim/figures.py`, `EXCLUDE`). The worst-case numbers in 6d do not change, because D = 400 was never the minimum.
- Figures use evenly spaced categorical x-axes and dodged 95% error bars (no more interpolated line from 0 to 25).

## 9. Figures available

- `report/figures/pcurve.png`: safety at D = 100 vs the auditor's per-decoy conviction rate p, with the analytic
  line 1 − (1 − p)^100 and the no-decoy baseline. **Candidate second headline**: it shows the condition (6f).
- `report/figures/{selfscreen,handdecoys,u05}/`: same plots for the sensitivity settings (u05 has no swarm plot).
- `report/figures/headline_frontier.png`: **headline**. Left: realistic auditor (all seven protocols overlap, because
  flooding self-incriminates). Right: pre-screened decoys (no protocol near the top-right; tripwire is safe but
  useless, the rest are useful but unsafe). Error bars = 95% CI of the worst-case configuration.
- `report/figures/{main,prescreen,perfect}/`: detect.png, degrade.png, swarm.png, swarm_degrade.png,
  frontier.png. CIs for the frontier points are in `results/<tag>/worst_case_ci.json`.

## 10. Related work (all IDs verified against the arXiv API on 2026-11-07)

| arXiv | Title | First author (et al.) | Date | Why cite |
|---|---|---|---|---|
| 2312.06942 | AI Control: Improving Safety Despite Intentional Subversion | Greenblatt (4 authors) | Dec 2023 | Trusted monitoring, defer-to-trusted, audit budget, global fallback. **Cite up front.** |
| 2504.10374 | Ctrl-Z: Controlling AI Agents via Resampling | Bhatt (8) | Apr 2025 | Audit budgets in agentic control; resampling as an alternative to deferral |
| 2602.20628 | When can we trust untrusted monitoring? A safety case sketch across collusion strategies | Gardner-Challis (7) | Feb 2026 | Closest prior idea: a colluding *monitor* wastes the budget. Ours: the *policy* fleet does it, with decoys |
| 2607.28317 | One Human, N Agents: Audit-Budget Allocation for LLM Agent Fleets under Miscalibrated, Correlated Confidence | Zavattari (3) | Jul 2026 | Fleet audit-budget allocation, non-adversarial: we add an adversary |
| 2606.08919 | Oversight Has a Capacity: Calibrating Agent Guards to a Subjective, Fatiguing Human | Turan (1) | Jun 2026 | Human audit capacity is finite |
| 2605.29178 | The Best-Laid SCHEMEs: Coordinated Sabotage and Monitoring in Multi-Agent Systems | Radev (4) | May 2026 | Detection-rate claims at fixed FPR assume no adversarial flooding |
| 2607.07368 | Multi-Agent AI Control: Distributed Attacks Hamper Per-Instance Monitors | Makins (4) | Jul 2026 | Distributed attacks vs per-instance monitors; matches our swarm result (6d) |

Before submitting, check the venue rules on citing arXiv (Apart accepts arXiv; this is not the coursework rule).
