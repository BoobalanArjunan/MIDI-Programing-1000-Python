#!/usr/bin/env python3
"""EFG_000060  -  minimal_cinematic, intensity 1 (sparse), 7/4 at 158 BPM, 2 active tracks in the main sections, profile E.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000060.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000060.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 60, "meter": "7/4", "tempo": 158, "tempo_band": "140-159", "style": "minimal_cinematic", "intensity": 1, "intensity_name": "sparse", "n_main": 2, "main_bucket": "1-2", "profile": "E", "groups_index": 0, "feel": "straight", "duration_target": 251.2, "seed": 910415}
EXPECTED_SHA256 = "13b4c03b6077cb9f6e5536d642c6a3e7bd473d616b45c00ca142310307449dff"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000060.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
