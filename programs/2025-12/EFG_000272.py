#!/usr/bin/env python3
"""EFG_000272  -  tribal_cinematic, intensity 1 (sparse), 9/8 at 75 BPM, 1 active tracks in the main sections, profile A.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000272.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000272.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 272, "meter": "9/8", "tempo": 75, "tempo_band": "60-79", "style": "tribal_cinematic", "intensity": 1, "intensity_name": "sparse", "n_main": 1, "main_bucket": "1-2", "profile": "A", "groups_index": 0, "feel": "straight", "duration_target": 263.5, "seed": 911901}
EXPECTED_SHA256 = "d63b922025ddf03a702fed29a058159b9dc8c013f5fbe72abed234b7c92c746e"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000272.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
