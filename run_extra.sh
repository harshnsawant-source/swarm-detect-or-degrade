#!/bin/sh
# Second chain (after run_all.sh): attacker self-screen settings and the decoy-conviction p-curve.
W=${1:-5}
set -e
cd "$(dirname "$0")"
run() { tag=$1; shift; echo "=== $tag $(date +%H:%M)"
  python sim/experiments.py --tag "$tag" --workers "$W" "$@" > "logs/exp_$tag.log" 2>&1
  python sim/paired.py "$tag" > "logs/paired_$tag.log" 2>&1
  python sim/figures.py "$tag" > "logs/figures_$tag.log" 2>&1; }
# attacker screens decoys with its OWN model (monitor rep 0 flags + own audit acquits), real auditor judges
run selfscreen --items items_v3.jsonl --decoys mild,hand --decoy_filter self --decoy_templates all
# p-curve: auditor-acquitted LLM decoys (real scores), decoy conviction rate set to p
for p in 0 0.003 0.01 0.03 0.1 0.3; do
  run "pcurve_$p" --decoy_filter acquitted --decoy_conv "$p" --grids detect
done
echo "=== EXTRA DONE $(date +%H:%M)"
