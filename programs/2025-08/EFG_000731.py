#!/usr/bin/env python3
"""EFG_000731  -  minimal_cinematic, intensity 2 (light), 4/4 at 96 BPM, 5 active tracks in the main sections, profile A.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000731.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000731.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 731, "meter": "4/4", "tempo": 96, "tempo_band": "80-99", "style": "minimal_cinematic", "intensity": 2, "intensity_name": "light", "n_main": 5, "main_bucket": "5-6", "profile": "A", "groups_index": 1, "feel": "straight", "duration_target": 297.9, "seed": 915110}
EXPECTED_SHA256 = "60586e876fd48fa08df05856a8f8a83cae625f61b3cc44754ff6d5eb7311f84d"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000731.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
