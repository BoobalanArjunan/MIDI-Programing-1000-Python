#!/usr/bin/env python3
"""EFG_000292  -  minimal_cinematic, intensity 5 (massive), 6/8 at 146 BPM, 8 active tracks in the main sections, profile B.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000292.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000292.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 292, "meter": "6/8", "tempo": 146, "tempo_band": "140-159", "style": "minimal_cinematic", "intensity": 5, "intensity_name": "massive", "n_main": 8, "main_bucket": "7-8", "profile": "B", "groups_index": 0, "feel": "straight", "duration_target": 244.3, "seed": 912040}
EXPECTED_SHA256 = "2f89c13bed0c6d23c18093896ee1802f1d15e70e13720af8c3049898f6ff0deb"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000292.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
