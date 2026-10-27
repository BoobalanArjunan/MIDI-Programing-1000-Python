#!/usr/bin/env python3
"""EFG_000129  -  trailer_action, intensity 4 (powerful), 7/8 at 123 BPM, 6 active tracks in the main sections, profile B.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000129.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000129.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 129, "meter": "7/8", "tempo": 123, "tempo_band": "120-139", "style": "trailer_action", "intensity": 4, "intensity_name": "powerful", "n_main": 6, "main_bucket": "5-6", "profile": "B", "groups_index": 1, "feel": "straight", "duration_target": 247.6, "seed": 910897}
EXPECTED_SHA256 = "ec05a4d1623bf0a4aa7c1a5cfa349043ce1843f38ddd8c2b9fb41e7c8eab3cff"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000129.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
