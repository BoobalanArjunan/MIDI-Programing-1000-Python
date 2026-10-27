#!/usr/bin/env python3
"""EFG_000763  -  trailer_action, intensity 2 (light), 7/8 at 118 BPM, 8 active tracks in the main sections, profile E.
Standalone program: regenerates this one arrangement as a 10-track Type-1 MIDI file.
Needs the ../engine folder (epic_gen.py, epic_elements.py, epic_compose.py, epic_arrange.py, epic_analysis.json).
Usage:  python EFG_000763.py [output_folder]      (default: ../output)
Result: <output_folder>/EFG_000763.mid  - byte-identical to full_arrangement.mid in the dataset (sha256 below)."""
import os, sys, json, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'engine'))
import epic_arrange as A
from epic_gen import learn, KITS

SPEC = {"index": 763, "meter": "7/8", "tempo": 118, "tempo_band": "100-119", "style": "trailer_action", "intensity": 2, "intensity_name": "light", "n_main": 8, "main_bucket": "7-8", "profile": "E", "groups_index": 2, "feel": "straight", "duration_target": 258.0, "seed": 915335}
EXPECTED_SHA256 = "a7ab33382a5b30720053b06dd374f4f7647319447f7c1b00029ace4decd1626b"

def main(out):
    K = learn(json.load(open(os.path.join(HERE, '..', 'engine', 'epic_analysis.json')))['files'])
    for k in KITS: K[k]['kit'] = k
    s = SPEC
    tracks, meter, info = A.build_one(K, s['index'], s['meter'], s['feel'], s['groups_index'], s['tempo'], s['seed'], s)
    data = A.write_smf(tracks, meter, s['tempo'], info['total_ticks'])
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, 'EFG_000763.mid')
    open(path, 'wb').write(data)
    ok = hashlib.sha256(data).hexdigest() == EXPECTED_SHA256
    print(path, info['total_bars'], 'bars', info['duration_seconds'], 's', 'identical to dataset file' if ok else 'DIFFERENT from dataset file')

if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'output'))
