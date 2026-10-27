#!/usr/bin/env python3
"""Epic Percussion variations: 100 new files per kit, many time signatures, intro + groove + fill + ending.
Style (key palette, velocity habits, layering, timing feel, note lengths, density) is LEARNED from the user's 111 loops;
rhythms are composed fresh, nothing is copied.
Usage: epic_gen.py <epic_analysis.json> <out_dir> [count_per_kit]
"""
import csv, json, math, os, random, struct, sys, zipfile
from collections import Counter, defaultdict

PPQ = 480
KITS = ['02 Taiko', '03 Epic Toms', '04 Metal Toms', '05 Concert Toms', '06 War Ensemble',
        '07 Solid Snare', '08 Snare Trio', '09 Ethtic Ensemble', '10 Hand Percussion', '14 Hi Percussion']
CASCADE_KITS = {'02 Taiko', '03 Epic Toms', '04 Metal Toms', '05 Concert Toms', '06 War Ensemble'}

# u = ticks per unit (480 quarter / 240 eighth); groups are in units; cc = MIDI clocks per click for the TS meta
METERS = {
    '2/4':  dict(n=2,  d=4, u=480, cc=24, groups=[[1, 1]]),
    '3/4':  dict(n=3,  d=4, u=480, cc=24, groups=[[1, 1, 1]]),
    '4/4':  dict(n=4,  d=4, u=480, cc=24, groups=[[1, 1, 1, 1], [2, 2]]),
    '2/2':  dict(n=2,  d=2, u=480, cc=48, groups=[[2, 2]]),
    '5/4':  dict(n=5,  d=4, u=480, cc=24, groups=[[3, 2], [2, 3]]),
    '6/4':  dict(n=6,  d=4, u=480, cc=24, groups=[[3, 3], [2, 2, 2]]),
    '7/4':  dict(n=7,  d=4, u=480, cc=24, groups=[[4, 3], [3, 4], [2, 2, 3]]),
    '5/8':  dict(n=5,  d=8, u=240, cc=12, groups=[[3, 2], [2, 3]]),
    '6/8':  dict(n=6,  d=8, u=240, cc=36, groups=[[3, 3], [2, 2, 2]]),
    '7/8':  dict(n=7,  d=8, u=240, cc=12, groups=[[2, 2, 3], [3, 2, 2], [2, 3, 2]]),
    '9/8':  dict(n=9,  d=8, u=240, cc=36, groups=[[3, 3, 3], [2, 2, 2, 3]]),
    '10/8': dict(n=10, d=8, u=240, cc=12, groups=[[3, 3, 2, 2], [2, 2, 3, 3], [5, 5]]),
    '11/8': dict(n=11, d=8, u=240, cc=12, groups=[[3, 3, 3, 2], [2, 3, 3, 3], [3, 2, 3, 3]]),
    '12/8': dict(n=12, d=8, u=240, cc=36, groups=[[3, 3, 3, 3], [4, 4, 4], [2, 2, 2, 2, 2, 2]]),
}
METER_COUNTS = [('4/4', 20), ('3/4', 9), ('6/8', 9), ('12/8', 9), ('2/4', 6), ('7/8', 6), ('5/4', 6), ('10/8', 6),
                ('11/8', 6), ('7/4', 5), ('9/8', 5), ('6/4', 5), ('5/8', 4), ('2/2', 4)]
assert sum(c for _, c in METER_COUNTS) == 100
BARS_W = [(4, 20), (5, 10), (6, 25), (7, 10), (8, 35)]


def clamp(x, a, b):
    return max(a, min(b, x))


# ------------------------------------------------------------------ learn from the user's files
def learn(D):
    K = {}
    for kit in KITS:
        items = [(f, r) for f, r in D.items() if f.split(' (')[0] == kit]
        notes = [n for _, r in items for n in r['notes']]
        tot = len(notes)
        pf = Counter(n['p'] for n in notes)
        pv = {p: sum(n['v'] for n in notes if n['p'] == p) / pf[p] for p in pf}
        partners, stacks = defaultdict(Counter), 0
        dens = []
        for _, r in items:
            N = r['notes']
            st = 0
            for a, b in zip(N, N[1:]):
                if a['p'] != b['p'] and abs(b['t'] - a['t']) <= 12:
                    partners[a['p']][b['p']] += 1
                    partners[b['p']][a['p']] += 1
                    st += 1
            stacks += st
            dens.append((len(N) - st) / (r['eot'][-1] / PPQ))
        tim, lens = {}, {}
        for fl, g in (('straight', 120), ('triplet', 160)):
            offs, L = [], []
            for f, r in items:
                if ('(triplet)' in f) == (fl == 'triplet'):
                    for n in r['notes']:
                        offs.append(n['t'] - round(n['t'] / g) * g)
                        L.append(n['d'])
            nz = [o for o in offs if o != 0]
            sd = (sum(o * o for o in nz) / len(nz)) ** 0.5 if nz else 3
            tim[fl] = dict(p_exact=sum(1 for o in offs if o == 0) / len(offs), sd=clamp(sd, 3, 12))
            lens[fl] = [x for x in L if 30 <= x <= 700] or [120]
        rare_cut = max(2, int(0.01 * tot))
        pool = sorted(p for p in pf if pf[p] >= rare_cut)
        anchor = min(p for p in pf if pf[p] / tot >= 0.08)
        accents = sorted([p for p in pool if p != anchor], key=lambda p: -pv[p])[:3]
        body = sorted([p for p in pool if p != anchor], key=lambda p: pv[p])
        K[kit] = dict(pf=dict(pf), pv=pv, partners={p: dict(c) for p, c in partners.items()},
                      p_stack=stacks / (tot - stacks), dens=sum(dens) / len(dens), tim=tim, lens=lens,
                      pool=pool, anchor=anchor, accents=accents, body=body,
                      seq=(sum(1 for x in lens['straight'] if x == 120) / len(lens['straight'])) >= 0.4,
                      palette=sorted(pf))
    return K


# ------------------------------------------------------------------ MIDI writer
def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def write_midi(name, meter, notes, total):
    ev = []
    nm = name.encode('ascii')
    ev.append((0, -2, b'\xFF\x03' + vlq(len(nm)) + nm))
    dd = {2: 1, 4: 2, 8: 3}[meter['d']]
    ev.append((0, -1, b'\xFF\x58\x04' + bytes([meter['n'], dd, meter['cc'], 8])))
    for t, d, p, v in notes:
        ev.append((t, 2, bytes([0x90, p, v])))
        ev.append((min(t + d, total), 0, bytes([0x80, p, 0])))
    data, last = b'', 0
    for t, _, b in sorted(ev, key=lambda e: (e[0], e[1])):
        data += vlq(t - last) + b
        last = t
    data += vlq(total - last) + b'\xFF\x2F\x00'
    return b'MThd' + struct.pack('>IHHH', 6, 1, 1, PPQ) + b'MTrk' + struct.pack('>I', len(data)) + data


# ------------------------------------------------------------------ composition
def layout(meter, groups, feel):
    us = 2 if meter['u'] == 240 else (4 if feel == 'straight' else 3)
    g = 160 if (meter['u'] == 480 and feel == 'triplet') else 120
    gs = [x * us for x in groups]
    starts = [0]
    for L in gs[:-1]:
        starts.append(starts[-1] + L)
    S = sum(gs)
    gi_of, j_of, L_of = [], [], []
    for gi, L in enumerate(gs):
        for j in range(L):
            gi_of.append(gi); j_of.append(j); L_of.append(L)
    assert S * g == sum(groups) * meter['u']
    return dict(g=g, gs=gs, starts=starts, S=S, bar=S * g, gi=gi_of, j=j_of, L=L_of, ng=len(gs))


def strength(lay, s):
    gi, j, L = lay['gi'][s], lay['j'][s], lay['L'][s]
    if j == 0:
        if gi == 0:
            return 1.0
        return 0.9 if (lay['ng'] == 4 and gi == 2) else 0.8
    if L >= 4 and L % 2 == 0 and j == L // 2:
        return 0.55
    if j == L - 1:
        return 0.5
    return 0.35


ARCH_FAC = dict(pulse=0.6, halftime=0.45, gallop=1.0, sync=0.9, ostinato=1.1)


def arch_mod(lay, arch, s):
    gi, j, L = lay['gi'][s], lay['j'][s], lay['L'][s]
    if arch == 'pulse':
        return 4 if j == 0 else 1
    if arch == 'halftime':
        if s == 0:
            return 6
        return 4 if (j == 0 and gi == lay['ng'] // 2) else 0.3
    if arch == 'gallop':
        return 3 if (j == 0 or j >= L - 2) else 0.4
    if arch == 'sync':
        return 3 if j == L - 1 else (1.5 if j == 0 else 0.6)
    if arch == 'ostinato':
        return 1.3 if j % 2 == 0 else 1
    return 1


def make_cell(rng, lay, arch, K, level, limit=None):
    S = lay['S'] if limit is None else limit
    beats = lay['bar'] / PPQ
    if arch == 'roll':
        k = round(lay['S'] * (0.7 + 0.25 * level))
    else:
        d = clamp(K['dens'], 0.6, 3.2) * (0.65 + 0.7 * level) * ARCH_FAC[arch]
        k = round(d * beats)
    k = int(clamp(k, min(lay['ng'], S), S))
    chosen = {0} if S > 0 else set()
    cand = list(range(1, S))
    while len(chosen) < k and cand:
        w = [strength(lay, s) ** 2 * arch_mod(lay, arch, s) + 0.02 for s in cand]
        s = rng.choices(cand, weights=w)[0]
        chosen.add(s)
        cand.remove(s)
    return chosen


def mutate(rng, lay, cell, p=0.12):
    out = set(cell)
    for s in range(1, lay['S']):
        if rng.random() < p:
            if s in out:
                out.discard(s)
            else:
                out.add(s)
    return out


class Piece:
    def __init__(self, K, lay, feel, rng, total):
        self.K, self.lay, self.rng, self.total = K, lay, rng, total
        self.fs = 'triplet' if feel == 'triplet' else 'straight'
        self.notes = []

    def off(self):
        t = self.K['tim'][self.fs]
        if self.rng.random() < t['p_exact']:
            return 0
        return int(clamp(round(self.rng.gauss(0, t['sd'])), -14, 14))

    def pick(self, s_strength, level=0.7):
        K, rng = self.K, self.rng
        w = []
        for p in K['pool']:
            x = K['pf'][p] * math.exp((K['pv'][p] - 90) / 22 * (2 * s_strength - 1) * 1.4)
            if p == K['anchor'] and s_strength >= 0.9:
                x *= 2.5
            w.append(x)
        return rng.choices(K['pool'], weights=w)[0]

    def vel_for(self, p, s_strength, level):
        v = self.K['pv'][p] + (s_strength - 0.55) * 34 + (level - 0.6) * 14 + self.rng.gauss(0, 5)
        return int(clamp(round(v), 38, 127))

    def add(self, t, p, v, d=None, exact=False, stack_chance=None, s_strength=0.5, level=0.7):
        rng, K = self.rng, self.K
        t = max(0, int(t) + (0 if exact else self.off()))
        if t >= self.total:
            return
        if d is None:
            d = rng.choice(K['lens'][self.fs])
        self.notes.append([t, d, p, int(clamp(v, 38, 127))])
        sc = (K['p_stack'] * (1.8 if s_strength >= 0.55 else 0.6)) if stack_chance is None else stack_chance
        if sc and rng.random() < sc and p in K['partners']:
            pc = K['partners'][p]
            q = rng.choices(list(pc), weights=list(pc.values()))[0]
            po = 0 if K['seq'] else int(clamp(rng.gauss(0, 2), -4, 4))
            self.notes.append([max(0, t + po), d, q, int(clamp(v + rng.gauss(-3, 5), 38, 127))])

    def hit(self, bi, s, strength_, level, p=None, v=None, **kw):
        lay = self.lay
        t = bi * lay['bar'] + s * lay['g']
        if p is None:
            p = self.pick(strength_, level)
        if v is None:
            v = self.vel_for(p, strength_, level)
        self.add(t, p, v, s_strength=strength_, level=level, **kw)


def compose(K, mname, groups, feel, N, seed):
    meter = METERS[mname]
    lay = layout(meter, groups, feel)
    rng = random.Random(seed)
    total = N * lay['bar']
    P = Piece(K, lay, feel, rng, total)
    S, starts, gs = lay['S'], lay['starts'], lay['gs']
    anchor, body, accents = K['anchor'], K['body'], K['accents']
    lowbody = body[0]

    dclass = 'dense' if K['dens'] >= 2.2 else ('mid' if K['dens'] >= 1.2 else 'low')
    AW = dict(dense=[('roll', 3), ('sync', 2), ('gallop', 1), ('ostinato', 2)],
              mid=[('sync', 2), ('gallop', 2), ('pulse', 1), ('ostinato', 2), ('roll', 1)],
              low=[('pulse', 2), ('halftime', 2), ('gallop', 2), ('sync', 2)])[dclass]
    arch = rng.choices([a for a, _ in AW], weights=[w for _, w in AW])[0]
    alts = [a for a, _ in AW if a != arch]
    arch2 = rng.choice(alts)

    intro_len = 1 if N <= 5 else rng.choice([1, 2, 2])
    fill_bi, end_bi = N - 2, N - 1
    body_bars = list(range(intro_len, fill_bi))
    B = len(body_bars)
    intro_style = rng.choice(['swell', 'hit-hold', 'roll-in', 'heartbeat'])
    fill_mode = rng.choice(['every', 'every', 'alt'])
    end_style = rng.choice(['decay', 'decay', 'double', 'rollout', 'solo'])

    def frac(bi, s):
        return (bi * lay['bar'] + s * lay['g']) / (intro_len * lay['bar'])

    # ---------------- intro
    skip_first = rng.random() < 0.15 and lay['ng'] >= 3
    for bi in range(intro_len):
        for gi, st in enumerate(starts):
            f = frac(bi, st)
            last_group_of_intro = (bi == intro_len - 1 and gi == lay['ng'] - 1)
            if intro_style == 'swell':
                if not (bi == 0 and gi == 0 and skip_first) and not last_group_of_intro:
                    P.hit(bi, st, 1, 0.5, p=anchor, v=int(44 + 48 * f + rng.gauss(0, 3)), stack_chance=0)
            elif intro_style == 'hit-hold':
                if bi == 0 and gi == 0:
                    P.hit(bi, 0, 1, 1, p=anchor, v=rng.randint(116, 124), d=(1440 if not K['seq'] else 480), stack_chance=0.9)
                    for a in accents[:1]:
                        P.add(0, a, rng.randint(112, 120), d=480, exact=True, stack_chance=0)
                elif not last_group_of_intro:
                    P.hit(bi, st, 0.8, 0.5, p=anchor, v=int(50 + 34 * f + rng.gauss(0, 3)), stack_chance=0)
            elif intro_style == 'heartbeat':
                if not last_group_of_intro and not (bi == 0 and gi == 0 and skip_first):
                    v = int(56 + 36 * f)
                    P.hit(bi, st, 1, 0.5, p=anchor, v=v + rng.randint(-3, 3), stack_chance=0)
                    P.hit(bi, st + max(1, gs[gi] // 2), 0.5, 0.5, p=lowbody, v=v - 22 + rng.randint(-3, 3), stack_chance=0)
            else:  # roll-in
                for s in range(gs[gi]):
                    ss = st + s
                    ff = frac(bi, ss)
                    if s == 0:
                        P.hit(bi, ss, 1, 0.5, p=anchor, v=int(62 + 30 * ff + rng.gauss(0, 3)), stack_chance=0)
                    if not last_group_of_intro:
                        P.hit(bi, ss, 0.3, 0.5, p=lowbody, v=int(34 + 50 * ff + rng.gauss(0, 3)), stack_chance=0)
            if last_group_of_intro:           # pickup crescendo into the groove
                n = min(gs[gi], 4 if lay['g'] == 120 else 3)
                for k in range(n):
                    ss = st + gs[gi] - n + k
                    v = int(78 + 28 * k / max(1, n - 1))
                    P.hit(bi, ss, 0.6, 0.7, p=(anchor if k % 2 == 0 else lowbody), v=v, stack_chance=0)

    # ---------------- intro safety pass (uses its own RNG, so nothing else in the file changes):
    # 1) a file never starts late: put back the downbeat hit(s) that a "skipped first hit" removed
    # 2) no gap longer than 3 beats inside the intro: add a soft pulse hit in the middle of any such gap
    P2 = Piece(K, lay, feel, random.Random(seed ^ 0x5F5F5F), total)
    P2.notes = P.notes
    if skip_first:
        if intro_style == 'swell':
            P2.hit(0, 0, 1, 0.5, p=anchor, v=int(44 + P2.rng.gauss(0, 3)), stack_chance=0)
        elif intro_style == 'heartbeat':
            v0 = int(56 + P2.rng.gauss(0, 2))
            P2.hit(0, 0, 1, 0.5, p=anchor, v=v0, stack_chance=0)
            P2.hit(0, max(1, gs[0] // 2), 0.5, 0.5, p=lowbody, v=v0 - 22, stack_chance=0)
    ib_end = intro_len * lay['bar']
    for _ in range(5):
        on = sorted({n[0] for n in P.notes if n[0] < ib_end})
        added = False
        for a_, b_ in zip(on, on[1:]):
            if b_ - a_ > 3 * PPQ:
                va = min([n[3] for n in P.notes if abs(n[0] - a_) <= 20])
                vb = min([n[3] for n in P.notes if abs(n[0] - b_) <= 20])
                if va >= 100:
                    va = vb - 12
                v = int(clamp((va + vb) / 2, 40, 100))
                s_abs = round((a_ + (b_ - a_) // 2) / lay['g'])
                bi_, s_ = divmod(s_abs, S)
                P2.hit(bi_, s_, strength(lay, s_), 0.5, p=anchor, v=v, stack_chance=0)
                added = True
        if not added:
            break

    # ---------------- groove
    base_cell = make_cell(rng, lay, arch, K, 0.7)
    for j, bi in enumerate(body_bars):
        level = 0.5 + 0.45 * j / max(1, B - 1)
        if B >= 3 and j == B // 2:
            cell = make_cell(rng, lay, arch2, K, level)
        else:
            cell = make_cell(rng, lay, arch, K, level) if j == 0 else mutate(rng, lay, base_cell)
            if j == 0:
                base_cell = set(cell)
        if j == B - 1:
            cell = set(cell) | {S - 1}
        for s in sorted(cell):
            P.hit(bi, s, strength(lay, s), level)

    # ---------------- fill (second half of bar N-1), groove before it
    fs_group = max(1, lay['ng'] // 2)
    fstart = starts[fs_group]
    pre = make_cell(rng, lay, arch, K, 0.95, limit=fstart)
    for s in sorted(pre):
        P.hit(fill_bi, s, strength(lay, s), 0.95)
    steps = list(range(fstart, S))
    if fill_mode == 'alt':
        steps = [s for s in steps if (s - fstart) % 2 == 0 or s >= S - lay['gs'][-1]]
    n = len(steps)
    cascade = K_is_cascade = (K['kit'] in CASCADE_KITS)
    pool = [p for p in K['body']] or [anchor]
    desc = rng.random() < 0.5
    pr = pool[::-1] if desc else pool
    for k, s in enumerate(steps):
        x = k / max(1, n - 1)
        v = int(62 + 56 * (x ** 1.1) + rng.gauss(0, 3))
        if k == n - 1:
            P.hit(fill_bi, s, 1, 1, p=anchor, v=124, stack_chance=0)
            P.add(fill_bi * lay['bar'] + s * lay['g'], accents[0], 120, exact=True, stack_chance=0)
            continue
        if cascade:
            p = pr[min(len(pr) - 1, int(k * len(pr) / n))]
        else:
            p = pr[0] if (k % 2 == 0) else pr[min(1, len(pr) - 1)]
        if lay['j'][s] == 0:
            v = min(127, v + 8)
        P.hit(fill_bi, s, 0.5 + 0.5 * x, 0.9, p=p, v=v, stack_chance=(0.35 if x > 0.6 else 0))

    # ---------------- ending
    tb = end_bi * lay['bar']
    big_d = int(min(1440, lay['bar'] * 0.75)) if not K['seq'] else 480
    P.add(tb, anchor, 127, d=big_d, exact=(K['seq'] or rng.random() < 0.7), stack_chance=0)
    for a, v in zip(accents[:2], (126, 122)):
        P.add(tb + (0 if K['seq'] else rng.randint(0, 3)), a, v, d=big_d, exact=True, stack_chance=0)
    if end_style == 'decay':
        gstarts = starts[1:]
        pick = gstarts[-3:] if len(gstarts) >= 3 else gstarts
        for v, st in zip((76, 58, 44), pick):
            P.add(tb + st * lay['g'], lowbody if rng.random() < 0.5 else anchor, v, stack_chance=0)
    elif end_style == 'double':
        gi2 = max(1, lay['ng'] // 2)
        t2 = tb + starts[gi2] * lay['g']
        P.add(t2, anchor, 118, d=big_d // 2, stack_chance=0)
        P.add(t2 + 2, accents[0], 114, d=big_d // 2, exact=True, stack_chance=0)
        P.add(tb + starts[-1] * lay['g'], lowbody, 54, stack_chance=0)
    elif end_style == 'rollout':
        st = starts[1]
        for k in range(gs[1]):
            P.add(tb + (st + k) * lay['g'], lowbody, int(80 - 36 * k / max(1, gs[1] - 1)), stack_chance=0)
    # 'solo' = the big hit only

    # ---------------- finalise: remove same-pitch overlaps, bound to total
    notes = sorted(P.notes, key=lambda n: (n[0], -n[3], n[2]))
    last, kept = {}, []
    for n in notes:
        t, d, p, v = n
        if t >= total:
            continue
        if p in last and t - last[p][0] < 40:        # same pitch twice within 40 ticks: keep the earlier
            continue
        if p in last and t < last[p][0] + last[p][1] + 15:
            last[p][1] = max(20, t - last[p][0] - 15)
        last[p] = n
        kept.append(n)
    out = [(t, int(min(d, total - t)), p, v) for t, d, p, v in kept]
    meta = dict(arch=arch, arch2=arch2 if B >= 3 else '', intro=intro_style, intro_bars=intro_len,
                fill=fill_mode, ending=end_style, bar_ticks=lay['bar'], groups='+'.join(map(str, groups)))
    return out, total, meter, meta


def feel_label(mname, feel):
    if METERS[mname]['u'] == 480:
        return feel
    return 'compound' if mname in ('6/8', '9/8', '12/8') else 'odd'


def section_map(N, ib, has_var):
    """per-bar section labels, e.g. intro|groove|variation|groove|fill|ending"""
    B = (N - 2) - ib
    out = []
    for b in range(N):
        if b < ib:
            out.append('intro')
        elif b == N - 2:
            out.append('fill')
        elif b == N - 1:
            out.append('ending')
        else:
            out.append('variation' if (has_var and (b - ib) == B // 2) else 'groove')
    return '|'.join(out)


def main(analysis, out_dir, per_kit=100, batch=0, idx_start=1):
    D = json.load(open(analysis))['files']
    K = learn(D)
    for k in KITS:
        K[k]['kit'] = k
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    for ki, kit in enumerate(KITS):
        rng = random.Random(5000 + ki + 7777 * batch)
        plan = []
        for mname, cnt in METER_COUNTS:
            cnt = round(cnt * per_kit / 100)
            for c in range(cnt):
                feel = ('straight' if c % 2 == 0 else 'triplet') if METERS[mname]['u'] == 480 else 'straight'
                groups = rng.choice(METERS[mname]['groups'])
                N = rng.choices([b for b, _ in BARS_W], weights=[w for _, w in BARS_W])[0]
                plan.append((mname, feel, groups, N))
        order = {m: i for i, (m, _) in enumerate(METER_COUNTS)}
        plan.sort(key=lambda x: (order[x[0]], x[1], x[3]))
        kd = os.path.join(out_dir, kit)
        os.makedirs(kd, exist_ok=True)
        for idx, (mname, feel, groups, N) in enumerate(plan, idx_start):
            seed = 10_000_000 * batch + 100000 * (ki + 1) + idx
            notes, total, meter, meta = compose(K[kit], mname, groups, feel, N, seed)
            fl = feel_label(mname, feel)
            fname = f"{kit} ({mname.replace('/', '-')} {fl} {N}b)({idx:03d}).mid"
            open(os.path.join(kd, fname), 'wb').write(write_midi(kit, meter, notes, total))
            rows.append([f"{kit}/{fname}", kit, mname, fl, meta['groups'], N, meta['arch'], meta['arch2'], meta['intro'],
                         meta['intro_bars'], meta['fill'], meta['ending'], len(notes), round(total / 960, 2),
                         section_map(N, meta['intro_bars'], bool(meta['arch2']))])
    with open(os.path.join(out_dir, 'index.csv'), 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['file', 'kit', 'time_signature', 'feel', 'beat_grouping_eighths_or_beats', 'bars', 'groove_type',
                    'variation_bar_type', 'intro_style', 'intro_bars', 'fill_style', 'ending_style', 'notes',
                    'seconds_at_120bpm', 'section_map'])
        w.writerows(rows)
    print('files written:', len(rows))
    json.dump({k: dict(palette=v['palette'], anchor=v['anchor'], accents=v['accents']) for k, v in K.items()},
              open(os.path.join(os.path.dirname(os.path.abspath(out_dir)), 'epic_kit_model.json'), 'w'))


if __name__ == '__main__':
    a = sys.argv
    main(a[1], a[2], int(a[3]) if len(a) > 3 else 100, int(a[4]) if len(a) > 4 else 0, int(a[5]) if len(a) > 5 else 1)
