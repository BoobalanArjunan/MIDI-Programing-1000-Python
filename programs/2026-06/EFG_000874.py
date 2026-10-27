#!/usr/bin/env python3
"""EFG_000874  -  tension_build, intensity 3 (moderate), 3/4 at 89 BPM, 9 active tracks in the main sections, profile C.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000874.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000874.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 874, "meter": "3/4", "tempo": 89, "tempo_band": "80-99", "style": "tension_build", "intensity": 3, "intensity_name": "moderate", "n_main": 9, "main_bucket": "9-10", "profile": "C", "groups_index": 0, "feel": "triplet", "duration_target": 244.4, "seed": 916116}
EXPECTED_SHA256 = "0d6d1a63dfd9aa6e158ead2a932be253212b67dbbc4584e5c18d0a98a100fa12"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000874.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
