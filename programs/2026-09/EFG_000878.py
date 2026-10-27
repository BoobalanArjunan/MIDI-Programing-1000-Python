#!/usr/bin/env python3
"""EFG_000878  -  minimal_cinematic, intensity 5 (massive), 3/4 at 112 BPM, 10 active tracks in the main sections, profile B.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000878.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000878.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 878, "meter": "3/4", "tempo": 112, "tempo_band": "100-119", "style": "minimal_cinematic", "intensity": 5, "intensity_name": "massive", "n_main": 10, "main_bucket": "9-10", "profile": "B", "groups_index": 0, "feel": "straight", "duration_target": 292.9, "seed": 916140}
EXPECTED_SHA256 = "08ba06bdc8f8a2750a54c4904ef86702c680e5af8756bb8ea2f3c33f31edee55"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000878.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
