#!/usr/bin/env python3
"""EFG_000990  -  dark_cinematic, intensity 4 (powerful), 3/4 at 176 BPM, 9 active tracks in the main sections, profile E.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000990.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000990.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 990, "meter": "3/4", "tempo": 176, "tempo_band": "160-180", "style": "dark_cinematic", "intensity": 4, "intensity_name": "powerful", "n_main": 9, "main_bucket": "9-10", "profile": "E", "groups_index": 0, "feel": "triplet", "duration_target": 241.5, "seed": 916927}
EXPECTED_SHA256 = "6f79fee0e6a4a3a6ae2e5cf169406e251d4a04cab9d38aa7ce2a10111f7bc8bc"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000990.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
