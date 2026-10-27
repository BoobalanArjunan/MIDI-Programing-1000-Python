#!/usr/bin/env python3
"""EFG_000914  -  minimal_cinematic, intensity 3 (moderate), 9/8 at 78 BPM, 10 active tracks in the main sections, profile A.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000914.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000914.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 914, "meter": "9/8", "tempo": 78, "tempo_band": "60-79", "style": "minimal_cinematic", "intensity": 3, "intensity_name": "moderate", "n_main": 10, "main_bucket": "9-10", "profile": "A", "groups_index": 1, "feel": "straight", "duration_target": 273.9, "seed": 916393}
EXPECTED_SHA256 = "bb25dc1b051a9fb5cebd0371cb574c4dbed14344298778f1c25e301c89cd068b"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000914.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
