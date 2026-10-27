#!/usr/bin/env python3
"""EFG_000725  -  dark_cinematic, intensity 1 (sparse), 4/4 at 141 BPM, 4 active tracks in the main sections, profile A.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000725.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000725.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 725, "meter": "4/4", "tempo": 141, "tempo_band": "140-159", "style": "dark_cinematic", "intensity": 1, "intensity_name": "sparse", "n_main": 4, "main_bucket": "3-4", "profile": "A", "groups_index": 1, "feel": "straight", "duration_target": 262.0, "seed": 915071}
EXPECTED_SHA256 = "33729eb38d66e97439ab51f0c5b6d050b95d7fc721198b36a940a98bd3add2d0"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000725.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
