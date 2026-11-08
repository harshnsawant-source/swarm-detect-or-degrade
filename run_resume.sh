#!/bin/sh
# Resume after pausing on 2026-11-07 22:30. Already complete: main, prescreen, selfscreen, pcurve_0.
# Runs the remaining settings from run_all.sh and run_extra.sh one after another. Usage: sh run_resume.sh [workers]
W=${1:-5}
set -e
cd "$(dirname "$0")"
mkdir -p logs
run() { tag=$1; shift; echo "=== $tag $(date +%H:%M)"
  python sim/experiments.py --tag "$tag" --workers "$W" "$@" > "logs/exp_$tag.log" 2>&1
  python sim/paired.py "$tag" > "logs/paired_$tag.log" 2>&1
  python sim/figures.py "$tag" > "logs/figures_$tag.log" 2>&1; }
for p in 0.003 0.01 0.03 0.1 0.3; do
  run "pcurve_$p" --decoy_filter acquitted --decoy_conv "$p" --grids detect
done
python sim/figures.py pcurve > logs/figures_pcurve.log 2>&1
run perfect     --auditor none
run u05         --decoy_filter acquitted --u_trusted 0.5 --grids detect,degrade,swarm_degrade
run handdecoys  --decoys hand
python sim/figures.py headline > logs/figures_headline.log 2>&1
echo "=== ALL DONE $(date +%H:%M)"
