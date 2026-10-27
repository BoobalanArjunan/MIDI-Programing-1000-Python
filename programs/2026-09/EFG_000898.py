#!/usr/bin/env python3
"""EFG_000898  -  battle_sequence, intensity 2 (light), 4/4 at 78 BPM, 4 active tracks in the main sections, profile C.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000898.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000898.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 898, "meter": "4/4", "tempo": 78, "tempo_band": "60-79", "style": "battle_sequence", "intensity": 2, "intensity_name": "light", "n_main": 4, "main_bucket": "3-4", "profile": "C", "groups_index": 0, "feel": "straight", "duration_target": 269.6, "seed": 916285}
EXPECTED_SHA256 = "4eab9d0487c254e2d3335d99b365bf6cc781e833231a10f0cf6ca0bd4565e7a3"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000898.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
