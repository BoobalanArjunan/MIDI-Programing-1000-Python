#!/usr/bin/env python3
"""Epic Percussion elements: loops, builds, breakdowns, climax, impacts. Style learned from the user's 111 loops.
Usage: epic_elements.py <epic_analysis.json> <out_dir> [scale]   (scale 1.0 = loops 150/kit, others 80/kit)"""
import csv, math, os, random, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epic_gen import (PPQ, KITS, CASCADE_KITS, METERS, METER_COUNTS, learn, layout, strength, make_cell, mutate,
                      Piece, write_midi, clamp)

COUNTS = dict(loop=150, build=80, breakdown=80, climax=80, impact=80)
BASE_SEED = dict(loop=200_000_000, build=300_000_000, breakdown=400_000_000, climax=500_000_000, impact=600_000_000)
ARCH_TXT = dict(pulse='a pulse on the beat groups', gallop='a long-short-short gallop', sync='syncopated accents',
                roll='a continuous accented roll', halftime='sparse half-time hits', ostinato='a driving ostinato')
BUILD_TXT = {'accel-pulse': 'an accelerating pulse (group hits, then subdivided hits, then rolls)',
             'swell-roll': 'a pulse that turns into a swelling roll',
             'layered-ostinato': 'an ostinato that gains more hits and layers each stage',
             'tom-climb': 'a climbing pattern that adds higher pitches as it rises'}
BREAK_TXT = {'stop-time': 'stop-time hits on the downbeat of each bar with silence between them',
             'heartbeat': 'a soft sparse lub-dub heartbeat',
             'ghost': 'one low hit and quiet ghost notes with long gaps',
             'call-response': 'a strong hit answered by a quiet echo, then silence',
             'single-pulse': 'a quiet single-note pulse on the beat groups'}
IMPACT_TXT = {'single': 'a single stacked full-velocity hit that rings',
              'single-decay': 'a stacked full-velocity hit followed by a decaying tail of soft hits',
              'double': 'two stacked hits, on the downbeat and in the middle of the bar',
              'triple': 'three stacked hits on consecutive beat groups, each a little softer',
              'flam': 'a flam: a soft grace hit just before a stacked full-velocity hit',
              'riser-hit': 'a one-bar crescendo roll landing on a stacked hit with a short tail',
              'hit-rollout': 'a stacked full-velocity hit followed by a soft decrescendo roll-out'}


def finalize(notes, total):
    notes = sorted(notes, key=lambda n: (n[0], -n[3], n[2]))
    last, kept = {}, []
    for n in notes:
        t, d, p, v = n
        if t >= total:
            continue
        if p in last and t - last[p][0] < 40:
            continue
        if p in last and t < last[p][0] + last[p][1] + 15:
            last[p][1] = max(20, t - last[p][0] - 15)
        last[p] = n
        kept.append(n)
    return [(t, int(max(20, min(d, total - t))), p, v) for t, d, p, v in kept]


def ctx(K, mname, groups, feel, nbars, seed):
    meter = METERS[mname]
    lay = layout(meter, groups, feel)
    rng = random.Random(seed)
    P = Piece(K, lay, feel, rng, nbars * lay['bar'])
    return meter, lay, rng, P


def dclass_of(K):
    return 'dense' if K['dens'] >= 2.2 else ('mid' if K['dens'] >= 1.2 else 'low')


# ------------------------------------------------------------------ 1. loops
def make_loop(K, mname, groups, feel, L, fclass, seed):
    meter, lay, rng, P = ctx(K, mname, groups, feel, L, seed)
    S, bar, g = lay['S'], lay['bar'], lay['g']
    anchor, body = K['anchor'], K['body']
    lowbody = body[0]
    AW = {'half-time': [('halftime', 7), ('pulse', 3)],
          'double-time': [('roll', 4), ('ostinato', 4), ('sync', 2)],
          'normal': {'dense': [('sync', 2), ('gallop', 1), ('ostinato', 2), ('roll', 1)],
                     'mid': [('sync', 2), ('gallop', 2), ('pulse', 1), ('ostinato', 2)],
                     'low': [('pulse', 2), ('gallop', 2), ('sync', 2)]}[dclass_of(K)]}[fclass]
    arch = rng.choices([a for a, _ in AW], weights=[w for _, w in AW])[0]
    level = 0.8
    A = make_cell(rng, lay, arch, K, level)
    memo = {}
    bars = [A, mutate(rng, lay, A, 0.15)] if L == 2 else [A, mutate(rng, lay, A, 0.12), A, mutate(rng, lay, A, 0.2)]
    for bi, cell in enumerate(bars):
        cell = set(cell)
        if bi == L - 1:
            cell.add(S - 1)                      # soft pickup that leads back to the loop start
        for s in sorted(cell):
            st = strength(lay, s)
            if s not in memo:
                p = P.pick(st, level)
                memo[s] = (p, P.vel_for(p, st, level))
            p, v = memo[s]
            v = v + (rng.randint(-2, 2) if bi > 0 else 0)
            if bi == L - 1 and s == S - 1:
                v = int(clamp(v, 40, 78))
            P.add(bi * bar + s * g, p, v, s_strength=st, level=level)
    tempo = {'half-time': (130, 174), 'normal': (92, 130), 'double-time': (68, 96)}[fclass]
    tempo = 2 * random.Random(seed ^ 0xBEEF).randint(tempo[0] // 2, tempo[1] // 2)
    return finalize(P.notes, L * bar), L * bar, dict(style=arch, fclass=fclass, tempo=tempo)


# ------------------------------------------------------------------ 2a. builds
def make_build(K, mname, groups, feel, N, style, seed):
    meter, lay, rng, P = ctx(K, mname, groups, feel, N, seed)
    S, bar, g = lay['S'], lay['bar'], lay['g']
    anchor, body, accents = K['anchor'], K['body'], K['accents']
    lowbody = body[0]
    pool_up = sorted(K['pool'])
    stage_cells, memo = [], {}
    if style == 'layered-ostinato':
        cur = set(make_cell(rng, lay, 'ostinato', K, 0.45))
        stage_cells.append(set(cur))
        for k in range(1, 4):
            cur |= make_cell(rng, lay, 'ostinato', K, 0.45 + 0.2 * k)
            stage_cells.append(set(cur))
    last = (N - 1, S - 1)
    for bi in range(N):
        for s in range(S):
            if (bi, s) == last:
                continue
            x = (bi * S + s) / (N * S)
            j, L, st = lay['j'][s], lay['L'][s], strength(lay, s)
            if style == 'accel-pulse':
                if x < 0.30:
                    on = j == 0
                elif x < 0.55:
                    on = j == 0 or (L >= 3 and j == L // 2)
                elif x < 0.80:
                    on = j == 0 or s % 2 == 0
                else:
                    on = True
                if not on:
                    continue
                p = anchor if j == 0 else (lowbody if x < 0.55 else rng.choice(body))
                v = 38 + 84 * x ** 1.05 + (8 if j == 0 else 0)
            elif style == 'swell-roll':
                if x < 0.18 and j != 0:
                    continue
                p = anchor if j == 0 else body[(s % 2) % len(body)]
                v = 34 + 86 * x + (12 if j == 0 else 0)
            elif style == 'layered-ostinato':
                if s not in stage_cells[min(3, int(x * 4))]:
                    continue
                if s not in memo:
                    memo[s] = P.pick(st, 0.6)
                p = memo[s]
                v = 36 + 84 * x + (8 if j == 0 else 0)
            else:  # tom-climb
                active = pool_up[:max(1, math.ceil(len(pool_up) * (0.25 + 0.75 * x)))]
                if x < 0.5 and not (j == 0 or s % 2 == 0):
                    continue
                p = active[-1] if j == 0 else active[(s + bi) % len(active)]
                v = 38 + 84 * x + (8 if j == 0 else 0)
            v = int(clamp(v + rng.gauss(0, 3), 38, 122))
            P.add(bi * bar + s * g, p, v, s_strength=st, level=0.7,
                  stack_chance=(0.25 if (x > 0.7 and j == 0) else 0))
    t_last = (N - 1) * bar + (S - 1) * g
    P.add(t_last, anchor, 124, stack_chance=0)
    for i, a in enumerate(accents[:2]):
        P.add(t_last, a, 120 - 2 * i, stack_chance=0)
    tempo = 2 * random.Random(seed ^ 0xBEEF).randint(45, 75)
    return finalize(P.notes, N * bar), N * bar, dict(style=style, tempo=tempo)


# ------------------------------------------------------------------ 2b. breakdowns
def make_breakdown(K, mname, groups, feel, N, style, seed):
    meter, lay, rng, P = ctx(K, mname, groups, feel, N, seed)
    S, bar, g, ng, starts, gs = lay['S'], lay['bar'], lay['g'], lay['ng'], lay['starts'], lay['gs']
    anchor, body, accents = K['anchor'], K['body'], K['accents']
    lowbody = body[0]
    for bi in range(N):
        b0 = bi * bar
        if style == 'stop-time':
            v0 = int(clamp(120 - 16 * bi, 66, 122))
            P.add(b0, anchor, v0, stack_chance=0)
            if bi == 0:
                for a in accents[:2]:
                    P.add(b0, a, v0 - 4, stack_chance=0, exact=True)
        elif style == 'heartbeat':
            v = int(52 + 8 * bi)
            P.add(b0, anchor, v, stack_chance=0)
            P.add(b0 + max(1, gs[0] // 2) * g, lowbody, v - 20, stack_chance=0)
            if ng >= 3:
                P.add(b0 + starts[1] * g, anchor, v - 6, stack_chance=0)
        elif style == 'ghost':
            P.add(b0, anchor, 88 if bi == 0 else 56, stack_chance=0)
            for s in range(1, S):
                j, L = lay['j'][s], lay['L'][s]
                if (j == L - 1 or (L >= 4 and j == L // 2)) and rng.random() < 0.35:
                    P.add(b0 + s * g, lowbody, int(40 + 12 * rng.random()), stack_chance=0)
        elif style == 'call-response':
            P.add(b0, anchor, 92, stack_chance=0)
            P.add(b0 + max(1, gs[0] // 2) * g, lowbody, 80, stack_chance=0)
            P.add(b0 + starts[1] * g, anchor, 52, stack_chance=0)
            P.add(b0 + (starts[1] + max(1, gs[1] // 2)) * g, lowbody, 42, stack_chance=0)
        else:  # single-pulse
            for gi in range(0, ng, 2 if ng >= 4 else 1):
                P.add(b0 + starts[gi] * g, anchor, int(52 + 6 * rng.random() + 4 * bi), stack_chance=0)
        if bi == N - 1:                                    # soft pickup crescendo into the next section
            n = min(3, S - 1)
            for k in range(n):
                P.add(b0 + (S - n + k) * g, anchor if k == n - 1 else lowbody, int(60 + 20 * k), stack_chance=0)
    tempo = 2 * random.Random(seed ^ 0xBEEF).randint(35, 65)
    return finalize(P.notes, N * bar), N * bar, dict(style=style, tempo=tempo)


# ------------------------------------------------------------------ 2c. climax
def make_climax(K, mname, groups, feel, N, seed):
    meter, lay, rng, P = ctx(K, mname, groups, feel, N, seed)
    S, bar, g, ng, starts = lay['S'], lay['bar'], lay['g'], lay['ng'], lay['starts']
    anchor, body, accents = K['anchor'], K['body'], K['accents']
    arch = rng.choices(['ostinato', 'gallop', 'roll', 'sync'], weights=[3, 3, 2, 2])[0]
    A = make_cell(rng, lay, arch, K, 1.0)
    memo = {}
    npk = min(4, S // 2)
    for bi in range(N):
        cell = set(A if bi % 2 == 0 else mutate(rng, lay, A, 0.12))
        if bi == N - 1:
            cell = {s for s in cell if s < S - npk}
        for s in sorted(cell):
            st = strength(lay, s)
            if s not in memo:
                p = P.pick(st, 1.0)
                memo[s] = (p, int(clamp(P.vel_for(p, st, 1.0) + 6, 38, 127)))
            p, v = memo[s]
            sc = min(0.55, K['p_stack'] * 2.2) if st >= 0.55 else None
            P.add(bi * bar + s * g, p, v + rng.randint(-2, 2), s_strength=st, level=1.0, stack_chance=sc)
        for gi in {0, ng // 2}:
            t = bi * bar + starts[gi] * g
            ps = [anchor] + (accents[:2] if (bi == 0 and gi == 0) else accents[:1])
            for p in ps:
                P.add(t, p, rng.randint(114, 126), stack_chance=0)
    b0 = (N - 1) * bar
    for k in range(npk):
        s = S - npk + k
        v = int(80 + 44 * k / max(1, npk - 1))
        P.add(b0 + s * g, anchor if k % 2 == 0 else body[0], v, stack_chance=0)
        if k == npk - 1:
            P.add(b0 + s * g, accents[0], 120, stack_chance=0)
    tempo = 2 * random.Random(seed ^ 0xBEEF).randint(50, 75)
    return finalize(P.notes, N * bar), N * bar, dict(style=arch, tempo=tempo)


# ------------------------------------------------------------------ 3. impacts / stingers
def make_impact(K, mname, groups, feel, itype, seed):
    N = 2 if itype == 'riser-hit' else 1
    meter, lay, rng, P = ctx(K, mname, groups, feel, N, seed)
    S, bar, g, ng, starts, gs = lay['S'], lay['bar'], lay['g'], lay['ng'], lay['starts'], lay['gs']
    anchor, body = K['anchor'], K['body']
    lowbody = body[0]
    if itype == 'triple' and ng < 3:
        itype = 'double'
    hot = sorted(set(K['accents'] + K['pool']), key=lambda p: -K['pv'][p])[:6]

    def stack():
        ps = ([anchor] if rng.random() < 0.85 else []) + rng.sample([p for p in hot if p != anchor],
                                                                    k=min(rng.choice([1, 2, 2, 3]), len(hot) - 1))
        return ps or [anchor]

    big_d = 480 if K['seq'] else int(rng.choice([960, 1440, int(bar * 0.75)]))

    def hit(t, ps, vtop, exact=False):
        for i, p in enumerate(ps):
            P.add(t, p, int(clamp(vtop - 2 * i - rng.randint(0, 1), 60, 127)), d=big_d, stack_chance=0,
                  exact=exact or K['seq'])

    ps = stack()
    if itype in ('single', 'single-decay', 'hit-rollout'):
        hit(0, ps, 127)
        if itype == 'single-decay':
            for v, st in zip((76, 56, 42), starts[1:][-3:]):
                P.add(st * g, lowbody if rng.random() < 0.5 else anchor, v, stack_chance=0)
        if itype == 'hit-rollout':
            for k in range(gs[1]):
                P.add((starts[1] + k) * g, lowbody, int(92 - 52 * k / max(1, gs[1] - 1)), stack_chance=0)
    elif itype == 'double':
        hit(0, ps, 127)
        hit(starts[ng // 2] * g, ps, 118)
    elif itype == 'triple':
        for v, st in zip((127, 116, 106), starts[:3]):
            hit(st * g, ps, v)
    elif itype == 'flam':
        P.add(0, anchor, 74, d=240, stack_chance=0, exact=True)
        hit(32, ps, 127, exact=True)
    else:  # riser-hit: bar 0 crescendo roll, bar 1 stack + tail
        for s in range(S):
            x = s / (S - 1)
            p = anchor if lay['j'][s] == 0 else body[(s % 2) % len(body)]
            P.add(s * g, p, int(34 + 78 * x + (10 if lay['j'][s] == 0 else 0)), stack_chance=0)
        hit(bar, ps, 127)
        for v, st in zip((76, 52), starts[1:][-2:]):
            P.add(bar + st * g, lowbody, v, stack_chance=0)
    tempo = 2 * random.Random(seed ^ 0xBEEF).randint(35, 80)
    return finalize(P.notes, N * bar), N * bar, dict(style=itype, tempo=tempo)


# ------------------------------------------------------------------ labels
def energy_of(vs):
    a = sum(vs) / len(vs)
    return 'low' if a < 70 else ('mid' if a < 92 else 'high')


def feel_text(feel_lbl, groups):
    base = {'straight': 'straight 16th feel', 'triplet': 'triplet feel', 'compound': 'compound feel',
            'odd': 'odd-meter feel'}[feel_lbl]
    return f"{base}, grouped {groups}"


def thirds(v):
    k = max(1, len(v) // 3)
    return round(sum(v[:k]) / k), round(sum(v[-k:]) / k)


def prompt(typ, kit, mname, flbl, grp, bars, meta, notes):
    srt = sorted(notes)
    vs = [n[3] for n in srt]
    kn, ts, ft = kit[3:], mname, feel_text(flbl, grp)
    avg = round(sum(vs) / len(vs))
    if typ == 'loop':
        return (f"{kn} loop in {ts} time ({ft}), {bars} bars, {meta['fclass']} feel, design tempo {meta['tempo']} BPM: "
                f"{ARCH_TXT[meta['style']]} with steady dynamics around velocity {avg}, {len(notes)} notes. It loops seamlessly.")
    if typ == 'build':
        a, b = thirds(vs)
        return (f"{kn} {bars}-bar build-up in {ts} time ({ft}), design tempo {meta['tempo']} BPM: {BUILD_TXT[meta['style']]}, "
                f"velocity rising from about {a} to about {b}, ending on a stacked hit. {len(notes)} notes.")
    if typ == 'breakdown':
        return (f"{kn} {bars}-bar breakdown in {ts} time ({ft}), design tempo {meta['tempo']} BPM: {BREAK_TXT[meta['style']]}, "
                f"soft dynamics (average velocity {avg}), ending with a short pickup into the next section. {len(notes)} notes.")
    if typ == 'climax':
        return (f"{kn} {bars}-bar climax in {ts} time ({ft}), design tempo {meta['tempo']} BPM: full-power {ARCH_TXT[meta['style']]} "
                f"with stacked accents, a landing stack on the first downbeat and a crescendo pickup at the end, "
                f"average velocity {avg}. {len(notes)} notes.")
    return (f"{kn} impact in {ts} time ({ft}), {bars} bar{'s' if bars > 1 else ''}: {IMPACT_TXT[meta['style']]}. "
            f"Peak velocity {max(vs)}, {len(notes)} notes.")


def feel_label(mname, feel):
    if METERS[mname]['u'] == 480:
        return feel
    return 'compound' if mname in ('6/8', '9/8', '12/8') else 'odd'


def distribute(n):
    raw = [(m, c * n / 100) for m, c in METER_COUNTS]
    base = [(m, int(x)) for m, x in raw]
    rest = n - sum(c for _, c in base)
    order = sorted(range(len(raw)), key=lambda i: -(raw[i][1] - base[i][1]))
    cnt = dict(base)
    for i in order[:rest]:
        cnt[raw[i][0]] += 1
    return cnt


def main(analysis, out_dir, scale=1.0):
    D = json.load(open(analysis))['files']
    K = learn(D)
    for k in KITS:
        K[k]['kit'] = k
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    FOLD = dict(loop='Loops', build='Builds', breakdown='Breakdowns', climax='Climax', impact='Impacts')
    for typ, per_kit in COUNTS.items():
        n = round(per_kit * scale)
        for ki, kit in enumerate(KITS):
            rng = random.Random(BASE_SEED[typ] + ki)
            cnt = distribute(n)
            plan = []
            for mname, c in cnt.items():
                for q in range(c):
                    feel = ('straight' if q % 2 == 0 else 'triplet') if METERS[mname]['u'] == 480 else 'straight'
                    plan.append([mname, feel, rng.choice(METERS[mname]['groups'])])
            rng.shuffle(plan)
            labels = {'loop': ['normal'] * 2 + ['half-time', 'double-time'],
                      'build': ['accel-pulse', 'swell-roll', 'layered-ostinato', 'tom-climb'],
                      'breakdown': ['stop-time', 'heartbeat', 'ghost', 'call-response', 'single-pulse'],
                      'climax': [''],
                      'impact': ['single', 'single-decay', 'double', 'triple', 'flam', 'riser-hit', 'hit-rollout']}[typ]
            for i, pl in enumerate(plan):
                pl.append(labels[i % len(labels)])
                pl.append({'loop': rng.choice([2, 4]), 'build': rng.choice([4, 6, 8]),
                           'breakdown': rng.choice([2, 3, 4]), 'climax': rng.choice([2, 3, 4]), 'impact': 0}[typ])
            order = {m: i for i, (m, _) in enumerate(METER_COUNTS)}
            plan.sort(key=lambda x: (order[x[0]], x[1], x[3], x[4]))
            seen = set()
            kd = os.path.join(out_dir, FOLD[typ], kit)
            os.makedirs(kd, exist_ok=True)
            for idx, (mname, feel, groups, lab, nb) in enumerate(plan, 1):
                for attempt in range(30):
                    seed = BASE_SEED[typ] + 100000 * (ki + 1) + idx + 1_000_003 * attempt
                    if typ == 'loop':
                        notes, total, meta = make_loop(K[kit], mname, groups, feel, nb, lab, seed)
                    elif typ == 'build':
                        notes, total, meta = make_build(K[kit], mname, groups, feel, nb, lab, seed)
                    elif typ == 'breakdown':
                        notes, total, meta = make_breakdown(K[kit], mname, groups, feel, nb, lab, seed)
                    elif typ == 'climax':
                        notes, total, meta = make_climax(K[kit], mname, groups, feel, nb, seed)
                    else:
                        notes, total, meta = make_impact(K[kit], mname, groups, feel, lab, seed)
                    sig = tuple(notes)
                    if sig not in seen:
                        seen.add(sig)
                        break
                bars = total // layout(METERS[mname], groups, feel)['bar']
                fl = feel_label(mname, feel)
                gtxt = '+'.join(map(str, groups))
                tag = typ + ' ' + (meta['fclass'] if typ == 'loop' else meta['style'])
                fname = f"{kit} ({mname.replace('/', '-')} {fl} {bars}b {tag})({idx:03d}).mid"
                open(os.path.join(kd, fname), 'wb').write(write_midi(kit, METERS[mname], notes, total))
                vs = [x[3] for x in notes]
                rows.append([f"{FOLD[typ]}/{kit}/{fname}", typ, kit, mname, fl, gtxt, bars, meta['style'],
                             meta.get('fclass', ''), meta['tempo'], energy_of(vs), len(notes), min(vs),
                             round(sum(vs) / len(vs)), max(vs), round(total / PPQ * 60 / meta['tempo'], 2),
                             prompt(typ, kit, mname, fl, gtxt, bars, meta, notes)])
            print(typ, kit, len(plan), flush=True)
    with open(os.path.join(out_dir, 'elements_index.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['file', 'type', 'kit', 'time_signature', 'feel', 'beat_grouping', 'bars', 'style', 'feel_class',
                    'design_tempo_bpm', 'energy', 'notes', 'vel_min', 'vel_avg', 'vel_max', 'seconds_at_design_tempo',
                    'text_prompt'])
        w.writerows(rows)
    print('elements written:', len(rows))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 1.0)
