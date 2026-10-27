#!/usr/bin/env python3
"""EFG_000240  -  dark_cinematic, intensity 4 (powerful), 6/8 at 89 BPM, 8 active tracks in the main sections, profile D.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000240.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000240.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 240, "meter": "6/8", "tempo": 89, "tempo_band": "80-99", "style": "dark_cinematic", "intensity": 4, "intensity_name": "powerful", "n_main": 8, "main_bucket": "7-8", "profile": "D", "groups_index": 1, "feel": "straight", "duration_target": 245.7, "seed": 911674}
EXPECTED_SHA256 = "7e65df8c3a1cf276d232204c3e780ee74a3b56a751ab812e42b2ed348f6de6b9"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000240.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
