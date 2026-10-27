#!/usr/bin/env python3
"""EFG_000637  -  battle_sequence, intensity 4 (powerful), 3/4 at 70 BPM, 3 active tracks in the main sections, profile E.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000637.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000637.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 637, "meter": "3/4", "tempo": 70, "tempo_band": "60-79", "style": "battle_sequence", "intensity": 4, "intensity_name": "powerful", "n_main": 3, "main_bucket": "3-4", "profile": "E", "groups_index": 0, "feel": "triplet", "duration_target": 273.7, "seed": 914454}
EXPECTED_SHA256 = "80a3713ac89224357065cfa614181b7d7d867c0ebfd0e38b0708ae90bf739e28"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000637.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
