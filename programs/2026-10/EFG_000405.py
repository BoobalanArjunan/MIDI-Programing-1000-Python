#!/usr/bin/env python3
"""EFG_000405  -  battle_sequence, intensity 4 (powerful), 9/8 at 146 BPM, 9 active tracks in the main sections, profile C.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000405.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000405.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 405, "meter": "9/8", "tempo": 146, "tempo_band": "140-159", "style": "battle_sequence", "intensity": 4, "intensity_name": "powerful", "n_main": 9, "main_bucket": "9-10", "profile": "C", "groups_index": 0, "feel": "straight", "duration_target": 280.2, "seed": 912833}
EXPECTED_SHA256 = "2eb8a1f73c37b57b8dca2f5be4b5622788111e4f9c28b73c72f2f053c376199c"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000405.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
