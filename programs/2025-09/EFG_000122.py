#!/usr/bin/env python3
"""EFG_000122  -  hybrid_percussion, intensity 1 (sparse), 4/4 at 137 BPM, 6 active tracks in the main sections, profile C.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000122.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000122.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 122, "meter": "4/4", "tempo": 137, "tempo_band": "120-139", "style": "hybrid_percussion", "intensity": 1, "intensity_name": "sparse", "n_main": 6, "main_bucket": "5-6", "profile": "C", "groups_index": 1, "feel": "triplet", "duration_target": 251.7, "seed": 910848}
EXPECTED_SHA256 = "266204947322c43a115ef31b2b4b0e82be9e57de2fc383cfcb93a3080b3029f0"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000122.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
