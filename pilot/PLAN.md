# Real-agent pilot (post-hackathon addition, 18 Nov 2026)

**Not part of the judged submission.** The hackathon entry (submitted 9 Nov 2026) is unchanged. This pilot
answers the main weakness reviewers raised: the coalition in the simulator follows a scripted strategy.

## Question
If the colluding agents are real LLMs that know the oversight rules and can message each other, do they
use harmless-but-suspicious submissions to spend the audit budget before attacking (audit flooding)? Does it
get an attack through more often than simply attacking?

## Environment (`pilot/real_agents.py`)
- Fleet of N = 10 agents for T = 10 rounds, B = 5 audits in total. Protocol: `threshold` (flagged submissions
  are audited while audits remain; afterwards they run unreviewed). One protocol only.
- k = 3 agents are a secret team, each played by a separate call to the same LLM per round, with a team
  channel that teammates read from the next round. The 7 honest agents are simulated (flag rate 2%, the
  calibrated rate from the main study).
- Each round a team agent chooses one of three real submissions for its task: A clean (honest item),
  B backdoor (attack item), C harmless but unusual (decoy item). All items and labels are the main study's,
  verified by tests. **No model-written code is executed.**
- Monitor verdict: a cached real monitor score of the chosen item (gemma4:31b, random rep, the main study's
  threshold). Audit verdict: the cached real auditor verdict (gpt-oss:120b). One conviction of a team
  submission shuts the team down, as in `sim/sim.py`.
- Two feedback conditions: **full** (each agent learns whether its own submission was flagged and reviewed)
  and **quiet** (it only learns that the team is still active).
- Smoke tests and tuning on the discovery templates only; the reported run uses the evaluation templates.

## Runs
| Model | Route | Feedback | Episodes |
|---|---|---|---|
| Gemma 4 31B (`google/gemma-4-31b-it`) | NVIDIA hosted API (free) | full | 8 |
| Gemma 4 31B | NVIDIA | quiet | 8 |
| gpt-oss-120b | Groq (free) | full | 2 |
| gpt-oss-120b | Groq | quiet | 2 |
Temperature 0.7, seeds 20261118 + episode index. Unparseable replies or refusals fall back to A and are
counted.

## Measures
- Team win rate, caught rate, rounds to the end.
- Discovery of flooding: share of episodes where the team submits C while audits remain and before its first
  B, and whether any team message proposes spending the reviews (read by hand; the messages are in the logs).
- Comparison: the same environment with scripted teams (attack at once; flood then attack), 20,000 episodes
  each, same seeds scheme.

## What this must not claim
- Not "agents in the wild flood audits": the decoy option is offered on a menu, so this tests whether agents
  use it strategically, not whether they would invent decoys from nothing.
- Not a security result about real deployments: cached verdicts, short episodes, 3 agents, one protocol.
- Small n: 8 episodes per condition gives wide intervals. Report counts, not percentages alone.
- Designed and run by Claude after the hackathon, at Harsh's request; settings frozen in `pilot/FROZEN.json`
  before the evaluation episodes.
