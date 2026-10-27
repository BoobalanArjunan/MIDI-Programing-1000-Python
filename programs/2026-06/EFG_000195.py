#!/usr/bin/env python3
"""EFG_000195  -  minimal_cinematic, intensity 2 (light), 4/4 at 65 BPM, 3 active tracks in the main sections, profile B.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000195.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000195.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 195, "meter": "4/4", "tempo": 65, "tempo_band": "60-79", "style": "minimal_cinematic", "intensity": 2, "intensity_name": "light", "n_main": 3, "main_bucket": "3-4", "profile": "B", "groups_index": 1, "feel": "straight", "duration_target": 293.4, "seed": 911359}
EXPECTED_SHA256 = "885342d5dcf50b1cde9ba22f226c140e26d5282db055b7e02b791c07ca0fd3b2"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000195.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
