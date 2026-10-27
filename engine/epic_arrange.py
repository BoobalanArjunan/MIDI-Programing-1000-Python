#!/usr/bin/env python3
"""EpicForge arrangement builder: 4-minute, 10-track (one per kit) Type-1 MIDI arrangements with an 11-section arc.
Style per kit is learned from the user's 111 originals (via epic_gen.learn). Rule-based / synthetic.
Usage: epic_arrange.py <epic_analysis.json> <dataset_root> [n=20] [batch=0]"""
import json, math, os, random, struct, sys, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epic_gen import PPQ, KITS, METERS, learn, layout, vlq, clamp
from epic_elements import make_loop, make_build, make_breakdown, make_climax, make_impact, finalize as _fin


def finalize(notes, total):
    return _fin([list(n) for n in notes], total)

GEN_VERSION = 'epicforge-arrange-1.0'
TARGET_SECONDS = 240
DURATION_TARGETS = [240, 252, 264, 276, 288, 300, 246, 258, 270, 282, 294, 240, 255, 267, 279, 291, 243, 261, 273, 285]   # seconds; every value is within 4:00-5:00
TRK = ['TRK_TAIKO', 'TRK_EPIC_TOMS', 'TRK_METAL_TOMS', 'TRK_CONCERT_TOMS', 'TRK_WAR', 'TRK_SOLID_SNARE',
       'TRK_SNARE_TRIO', 'TRK_ETHNIC', 'TRK_HAND', 'TRK_HI_PERC']
ROLE = ['primary_pulse', 'driving_pattern', 'accent', 'fills_and_sequences', 'ensemble_support', 'snare_pulse',
        'layered_snare', 'texture', 'hand_texture', 'high_detail']
# (section_type, file_slug, weight in the 120-bar template)
SECTIONS = [('INTRO', 'intro', 8), ('INTRO_BUILD', 'intro_build', 8), ('MAIN_GROOVE', 'main_groove_a', 16),
            ('GROOVE_VARIATION', 'groove_variation', 16), ('BUILD_UP', 'build_up_a', 8), ('CLIMAX', 'climax_a', 16),
            ('BREAKDOWN', 'breakdown', 8), ('MAIN_GROOVE', 'main_groove_b', 16), ('BUILD_UP', 'build_up_b', 8),
            ('CLIMAX', 'final_climax', 12), ('OUTRO', 'outro', 4)]
ENERGY_TARGET_OLD = [(.10, .20), (.20, .40), (.45, .55), (.55, .70), (.60, .85), (.90, .95), (.20, .15), (.50, .60),
                 (.65, .90), (.95, 1.0), (.60, .05)]
from epic_compose import LEVELS as ENERGY_TARGET
STYLE_OF = {0: 'accel-pulse', 1: 'tom-climb', 2: 'tom-climb', 3: 'tom-climb', 4: 'tom-climb', 5: 'swell-roll',
            6: 'swell-roll', 7: 'layered-ostinato', 8: 'layered-ostinato', 9: 'layered-ostinato'}
PILOT = [('4/4', 'straight', 0), ('4/4', 'straight', 1), ('4/4', 'triplet', 0), ('3/4', 'straight', 0),
         ('3/4', 'triplet', 0), ('6/8', 'straight', 0), ('6/8', 'straight', 1), ('12/8', 'straight', 0),
         ('12/8', 'straight', 1), ('2/4', 'straight', 0), ('7/8', 'straight', 0), ('7/8', 'straight', 1),
         ('5/4', 'straight', 0), ('10/8', 'straight', 0), ('11/8', 'straight', 0), ('7/4', 'straight', 0),
         ('9/8', 'straight', 1), ('6/4', 'straight', 1), ('5/8', 'straight', 0), ('2/2', 'straight', 0)]


def alloc_bars(total, wm=None):
    w = [s[2] * (wm or {}).get(i, 1.0) for i, s in enumerate(SECTIONS)]
    raw = [x * total / sum(w) for x in w]
    base = [max(2, int(r)) for r in raw]
    while sum(base) < total:
        i = max(range(len(w)), key=lambda i: raw[i] - base[i])
        base[i] += 1
    while sum(base) > total:
        i = max(range(len(w)), key=lambda i: base[i] - raw[i] if base[i] > 2 else -9)
        base[i] -= 1
    return base


def chunks(n):
    if n <= 4:
        return [n]
    k = math.ceil(n / 4)
    b, e = divmod(n, k)
    return [b + 1 if i < e else b for i in range(k)]


def vscale(notes, f):
    return [(t, d, p, int(clamp(round(v * f), 30, 127))) for t, d, p, v in notes]


def shift(notes, off, lim=None):
    out = []
    for t, d, p, v in notes:
        if lim is not None and t >= lim:
            continue
        out.append((t + off, d if lim is None else min(d, lim - t), p, v))
    return out


def write_smf(tracks, meter, tempo, total):
    """tracks: [(name, channel, notes)] -> Type 1 bytes. Tempo event in track 1 only; time signature in every track."""
    dd = {2: 1, 4: 2, 8: 3}[meter['d']]
    out = [b'MThd' + struct.pack('>IHHH', 6, 1, len(tracks), PPQ)]
    for i, tk in enumerate(tracks):
        name, ch, notes = tk[0], tk[1], tk[2]
        ccs = tk[3] if len(tk) > 3 else []
        ev = []
        nm = name.encode('ascii')
        ev.append((0, -3, b'\xFF\x03' + vlq(len(nm)) + nm))
        if i == 0:
            ev.append((0, -2, b'\xFF\x51\x03' + int(round(60_000_000 / tempo)).to_bytes(3, 'big')))
        ev.append((0, -1, b'\xFF\x58\x04' + bytes([meter['n'], dd, meter['cc'], 8])))
        for t, cc, val in ccs:
            if t >= total: continue
            ev.append((t, 1, bytes([0xB0 | ch, cc, val])))
        for t, d, p, v in notes:
            ev.append((t, 2, bytes([0x90 | ch, p, v])))
            ev.append((min(t + d, total), 0, bytes([0x80 | ch, p, 0])))
        data, last = b'', 0
        for t, _, b in sorted(ev, key=lambda e: (e[0], e[1])):
            data += vlq(t - last) + b
            last = t
        data += vlq(total - last) + b'\xFF\x2F\x00'
        out.append(b'MTrk' + struct.pack('>I', len(data)) + data)
    return b''.join(out)


# ------------------------------------------------------------------ section renderers (local ticks, one kit)
class Ctx:
    def __init__(self, K, mname, groups, feel):
        self.K, self.m, self.g, self.f = K, mname, groups, feel
        self.lay = layout(METERS[mname], groups, feel)
        self.bar = self.lay['bar']


def groove(c, kit, nb, sA, sB, fclass):
    notes, pos, u = [], 0, 0
    while pos < nb:
        L = min(4, nb - pos)
        nts, _, meta = make_loop(c.K[kit], c.m, c.g, c.f, 4, fclass, sA if u % 2 == 0 else sB)
        notes += shift(nts, pos * c.bar, L * c.bar)
        pos += L
        u += 1
    return finalize(notes, nb * c.bar), meta['style']


def climax(c, kit, nb, seed):
    notes, pos = [], 0
    for ci, n in enumerate(chunks(nb)):
        nts, _, meta = make_climax(c.K[kit], c.m, c.g, c.f, n, seed + (ci % 2))
        notes += shift(nts, pos * c.bar)
        pos += n
    return finalize(notes, nb * c.bar), meta['style']


def outro(c, kit, nb, seed, tail):
    itype = 'single-decay' if kit == KITS[0] else random.Random(seed).choice(['single', 'double', 'hit-rollout', 'single'])
    notes, _, _ = make_impact(c.K[kit], c.m, c.g, c.f, itype, seed)
    lay = c.lay
    if tail:
        for b in range(1, nb):
            v = int(66 - 38 * (b - 1) / max(1, nb - 2)) if nb > 2 else 52
            notes.append((b * c.bar, 480, c.K[kit]['anchor'], v))
            if lay['ng'] >= 2:
                notes.append((b * c.bar + lay['starts'][1] * lay['g'], 240, c.K[kit]['body'][0], max(30, v - 18)))
    return finalize(notes, nb * c.bar), itype


def kit_plan(rng):
    """which kits play in each section: returns list (per section) of dict kit_index -> kind"""
    pick = rng.choice
    lead = pick([0, 4, 1])
    tex = pick([7, 8, 9])
    A = [0, pick([1, 4]), pick([5, 6]), pick([7, 8]), 9]
    if rng.random() < 0.5:
        A.append(pick([2, 3]))
    A = list(dict.fromkeys(A))
    B = [0, 4 if 1 in A else 1, 6 if 5 in A else 5, 8 if 7 in A else 7, pick([2, 3]), 9]
    B = list(dict.fromkeys(B))
    var = list(dict.fromkeys(A + [x for x in (2, 3) if x not in A][:2] + [6 if 5 in A else 5]))
    bu_a = list(dict.fromkeys(var + [4 if 4 not in var else 1]))
    bu_b = [k for k in range(10) if k != pick([7, 8, 9, 3, 2])]
    plan = [
        {lead: 'stop-time', tex: 'single-pulse', **({pick([9, 8, 7]): 'ghost'} if rng.random() < .5 else {})},
        {lead: 'swell-roll', tex: 'accel-pulse', pick([5, 6]): 'layered-ostinato'},
        {k: 'groove' for k in A},
        {k: 'groove' for k in var},
        {k: 'build' for k in bu_a},
        {k: 'climax' for k in range(10)},
        {0: 'stop-time', pick([7, 8]): 'heartbeat', 9: 'ghost', **({2: 'call-response'} if rng.random() < .5 else {})},
        {k: 'groove' for k in B},
        {k: 'build' for k in bu_b},
        {k: 'climax' for k in range(10)},
        {k: 'outro' for k in range(10)},
    ]
    return plan, lead


def build_one(K, n, mname, feel, gidx, tempo, seed, spec=None):
    from epic_compose import Composer, LEVELS
    meter = METERS[mname]
    groups = meter['groups'][gidx]
    lay = layout(meter, groups, feel)
    bar = lay['bar']
    bar_sec = bar / PPQ * 60 / tempo
    # every file is at least 4:00 and at most 5:00; the extra time goes to the breakdown and the ending (and a little to the variation and final climax)
    target = spec['duration_target'] if spec else DURATION_TARGETS[(n - 1) % len(DURATION_TARGETS)]
    if spec:
        from epic_compose import STYLE_TAB
        swm = STYLE_TAB[spec['style']].get('secw')
    else:
        swm = None
    base_bars = max(22, round(TARGET_SECONDS / bar_sec))
    total_bars = math.ceil(target / bar_sec - 1e-9)
    if total_bars * bar_sec > 300.0: total_bars -= 1
    total_bars = max(total_bars, base_bars)
    nbs = alloc_bars(base_bars, swm)
    extra = total_bars - base_bars
    wts = {6: .35, 10: .35, 3: .15, 9: .15}
    adds = {i: int(extra * w) for i, w in wts.items()}
    for i in sorted(wts, key=lambda i: -(extra * wts[i] - adds[i]))[:extra - sum(adds.values())]:
        adds[i] += 1
    for i, a in adds.items(): nbs[i] += a
    # the breakdown needs room for its surprises and the ending room to resolve, whatever the tempo
    for i, secs in ((6, 22.0), (10, 10.0)):
        need = math.ceil(secs / bar_sec)
        while nbs[i] < need:
            donor = max((j for j in (2, 3, 7, 5, 9) if nbs[j] > 5), key=lambda j: nbs[j], default=None)
            if donor is None: break
            nbs[donor] -= 1; nbs[i] += 1
    C = Composer(K, mname, groups, feel, tempo, nbs, seed, spec).render()
    total = total_bars * bar
    ccs, ameta = C.automation()
    tracks = [(TRK[k], k, finalize(C.P[k].notes, total), ccs[k]) for k in range(10)]
    phrases = []
    for e in C.log:
        k, si = e['kit_index'], e['section_index'] - 1
        a0, a1 = C.starts[si] * bar, (C.starts[si] + nbs[si]) * bar
        cnt = sum(1 for t in tracks[k][2] if a0 <= t[0] < a1)
        phrases.append(dict(e, seed=seed * 1000 + si * 20 + k, bars=nbs[si], start_bar=C.starts[si] + 1, notes=cnt))
    plan = [dict() for _ in range(11)]
    for p in phrases:
        plan[p['section_index'] - 1][TRK[p['kit_index']]] = p['kind']
    entry = {str(si + 1): [dict(x, track_id=TRK[x['track_id']] if isinstance(x['track_id'], int) else x['track_id']) for x in v] for si, v in C.entry_plan.items()}
    info = dict(sample_id=f'EFG_{n:06d}', family_id=f'FAM_{n:06d}', time_signature=mname, feel=feel,
                beat_grouping='+'.join(map(str, groups)), groups=groups, tempo_bpm=tempo, total_bars=total_bars,
                bar_ticks=bar, grid_ticks=lay['g'], steps_per_bar=lay['S'], total_ticks=total,
                duration_seconds=round(total / PPQ * 60 / tempo, 3), seed=seed, groove_b_feel_class='normal',
                lead_kit=0, section_bars=nbs, section_starts=[s + 1 for s in C.starts], plan=plan, phrases=phrases,
                styles=C.styles, groove_style_a=C.M_A['style'], groove_style_b=C.M_B['style'], entry_plan=entry,
                transitions={str(k + 1): v for k, v in getattr(C, 'trans_choice', {}).items()},
                outro_roles={TRK[k]: v for k, v in C.outro_roles.items()}, outro_info=C.outro_info, automation=ameta,
                levels=[list(x) for x in C.LV])
    if spec:
        info.update(primary_style=spec['style'], intensity_label=spec['intensity'], intensity_name=spec['intensity_name'],
                    activity_profile=spec['profile'], n_main_planned=spec['n_main'], tempo_band=spec['tempo_band'],
                    duration_target_seconds=spec['duration_target'], track_order=[TRK[k] for k in C.order],
                    allowed_tracks={str(si + 1): [TRK[k] for k in sorted(v)] for si, v in C.allowed.items()},
                    cameo_tracks=[TRK[k] for k in C.cameo], alternating_groups=C.alt)
    return tracks, meter, info


def section_tracks(tracks, s0, s1):
    out = []
    for tk in tracks:
        name, ch, notes = tk[0], tk[1], tk[2]
        ccs = tk[3] if len(tk) > 3 else []
        ns = [(t - s0, min(d, s1 - t), p, v) for t, d, p, v in notes if s0 <= t < s1]
        if not ns:
            continue
        state = {}
        for t, cc, val in ccs:
            if t <= s0:
                state[cc] = val
        cs = [(0, cc, v) for cc, v in sorted(state.items())]
        cs += [(t - s0, cc, val) for t, cc, val in ccs if s0 < t < s1]
        out.append((name, ch, ns, cs))
    return out


_G = {}


def _init(analysis):
    D = json.load(open(analysis))['files']
    K = learn(D)
    for k in KITS:
        K[k]['kit'] = k
    _G['K'] = K


def _work(args):
    mdir, sp = args
    n = sp['index']
    K = _G['K']
    tracks, meter, info = build_one(K, n, sp['meter'], sp['feel'], sp['groups_index'], sp['tempo'], sp['seed'], sp)
    d = os.path.join(mdir, info['sample_id'])
    os.makedirs(os.path.join(d, 'sections'), exist_ok=True)
    os.makedirs(os.path.join(d, 'metadata'), exist_ok=True)
    data = write_smf(tracks, meter, sp['tempo'], info['total_ticks'])
    open(os.path.join(d, 'full_arrangement.mid'), 'wb').write(data)
    info['sha256'] = hashlib.sha256(data).hexdigest()
    info['sections'] = []
    for si, (stype, slug, _) in enumerate(SECTIONS):
        s0 = (info['section_starts'][si] - 1) * info['bar_ticks']
        s1 = s0 + info['section_bars'][si] * info['bar_ticks']
        fn = f'{si + 1:03d}_{slug}.mid'
        tr = section_tracks(tracks, s0, s1)
        sd = write_smf(tr, meter, sp['tempo'], s1 - s0)
        open(os.path.join(d, 'sections', fn), 'wb').write(sd)
        info['sections'].append(dict(index=si + 1, type=stype, slug=slug, file=fn, start_bar=info['section_starts'][si],
                                     bars=info['section_bars'][si], sha256=hashlib.sha256(sd).hexdigest(), tracks=[t[0] for t in tr]))
    return info


def main_plan(analysis, root, planfile, procs=2, lo=0, hi=None):
    plan = json.load(open(planfile))[lo:hi]
    mdir = os.path.join(root, '04_arrangements', 'multitrack_midi')
    os.makedirs(mdir, exist_ok=True)
    os.makedirs(os.path.join(root, '04_arrangements', 'section_midi'), exist_ok=True)
    import multiprocessing as mp
    mf = open(os.path.join(root, '04_arrangements', 'arrangement_manifest.jsonl'), 'w')
    with mp.Pool(procs, initializer=_init, initargs=(analysis,)) as pool:
        for c, info in enumerate(pool.imap(_work, [(mdir, sp) for sp in plan], chunksize=4), 1):
            mf.write(json.dumps(info) + '\n')
            if c % 50 == 0: print(c, info['sample_id'], flush=True)
    mf.close()


def main(analysis, root, n_files=20, batch=0):
    D = json.load(open(analysis))['files']
    K = learn(D)
    for k in KITS:
        K[k]['kit'] = k
    arr_dir = os.path.join(root, '04_arrangements')
    mdir = os.path.join(arr_dir, 'multitrack_midi')
    os.makedirs(mdir, exist_ok=True)
    os.makedirs(os.path.join(arr_dir, 'section_midi'), exist_ok=True)
    rng = random.Random(20261023 + batch)
    tempos = [60 + 5 * round(i * 24 / (n_files - 1)) for i in range(n_files)]
    rng.shuffle(tempos)
    plan = (PILOT * (n_files // len(PILOT) + 1))[:n_files]
    mf = open(os.path.join(arr_dir, 'arrangement_manifest.jsonl'), 'w')
    for i, ((mname, feel, gidx), tempo) in enumerate(zip(plan, tempos), 1):
        n = 100000 * batch + i
        seed = 7000 + n
        tracks, meter, info = build_one(K, n, mname, feel, gidx, tempo, seed)
        d = os.path.join(mdir, info['sample_id'])
        os.makedirs(os.path.join(d, 'sections'), exist_ok=True)
        os.makedirs(os.path.join(d, 'metadata'), exist_ok=True)
        data = write_smf(tracks, meter, tempo, info['total_ticks'])
        open(os.path.join(d, 'full_arrangement.mid'), 'wb').write(data)
        info['sha256'] = hashlib.sha256(data).hexdigest()
        info['sections'] = []
        for si, (stype, slug, _) in enumerate(SECTIONS):
            s0 = (info['section_starts'][si] - 1) * info['bar_ticks']
            s1 = s0 + info['section_bars'][si] * info['bar_ticks']
            fn = f'{si + 1:03d}_{slug}.mid'
            tr = section_tracks(tracks, s0, s1)
            sd = write_smf(tr, meter, tempo, s1 - s0)
            open(os.path.join(d, 'sections', fn), 'wb').write(sd)
            info['sections'].append(dict(index=si + 1, type=stype, slug=slug, file=fn,
                                         start_bar=info['section_starts'][si], bars=info['section_bars'][si],
                                         sha256=hashlib.sha256(sd).hexdigest(), tracks=[t[0] for t in tr]))
        mf.write(json.dumps(info) + '\n')
        print(info['sample_id'], mname, feel, tempo, 'bpm', info['total_bars'], 'bars', info['duration_seconds'], 's',
              flush=True)
    mf.close()


if __name__ == '__main__':
    if len(sys.argv) > 3 and sys.argv[3].endswith('.json'):
        main_plan(sys.argv[1], sys.argv[2], sys.argv[3]); sys.exit(0)
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 20,
         int(sys.argv[4]) if len(sys.argv) > 4 else 0)
