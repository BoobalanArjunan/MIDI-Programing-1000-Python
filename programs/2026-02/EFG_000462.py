#!/usr/bin/env python3
"""EFG_000462  -  hybrid_percussion, intensity 4 (powerful), 9/8 at 137 BPM, 3 active tracks in the main sections, profile A.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000462.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000462.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 462, "meter": "9/8", "tempo": 137, "tempo_band": "120-139", "style": "hybrid_percussion", "intensity": 4, "intensity_name": "powerful", "n_main": 3, "main_bucket": "3-4", "profile": "A", "groups_index": 1, "feel": "straight", "duration_target": 243.8, "seed": 913232}
EXPECTED_SHA256 = "d7fc400352611962891c45c739e589893c7e9b003ae2c48c68b696f3e551d105"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000462.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
