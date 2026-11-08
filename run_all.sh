#!/bin/sh
# Full experiment chain (sequential, to stay within memory). Each run: experiments -> paired -> figures.
# Usage: sh run_all.sh [workers]
W=${1:-5}
set -e
cd "$(dirname "$0")"
mkdir -p logs
run() {  # tag, extra args
  tag=$1; shift
  echo "=== $tag $(date +%H:%M)"
  python sim/experiments.py --tag "$tag" --workers "$W" "$@" > "logs/exp_$tag.log" 2>&1
  python sim/paired.py "$tag" > "logs/paired_$tag.log" 2>&1
  python sim/figures.py "$tag" > "logs/figures_$tag.log" 2>&1
}
run main                                                   # realistic auditor, all decoys
run prescreen   --decoy_filter acquitted                   # oracle pre-screen (auditor's own verdicts)
# 'predicted' (attacker pre-screens with gemma) is empty: gemma convicts all 127 LLM decoys. 'gap' for LLM decoys
# equals 'prescreen' (every acquitted decoy is gemma-convicted), so cascade is evaluated inside 'prescreen'.
run perfect     --auditor none                             # perfect auditor, innocent decoys
run u05         --decoy_filter acquitted --u_trusted 0.5 --grids detect,degrade,swarm_degrade
run handdecoys  --decoys hand                              # mild hand-written decoys, realistic auditor, no pre-screen
python sim/figures.py headline > logs/figures_headline.log 2>&1
echo "=== ALL DONE $(date +%H:%M)"
