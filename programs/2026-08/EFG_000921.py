#!/usr/bin/env python3
"""EFG_000921  -  battle_sequence, intensity 2 (light), 7/8 at 113 BPM, 3 active tracks in the main sections, profile E.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000921.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000921.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 921, "meter": "7/8", "tempo": 113, "tempo_band": "100-119", "style": "battle_sequence", "intensity": 2, "intensity_name": "light", "n_main": 3, "main_bucket": "3-4", "profile": "E", "groups_index": 2, "feel": "straight", "duration_target": 270.8, "seed": 916440}
EXPECTED_SHA256 = "2e0d52a2946d8bfa4acb253b930fb20aab0bb817a24d52a7c7b4c9881095cc6c"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000921.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
