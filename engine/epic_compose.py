#!/usr/bin/env python3
"""EpicForge composition planner + renderer (v2). Follows the owner's 'Section Creations' specification:
per-section instrument-entry plans, 4-bar phrase development, several styles per section, track ending roles and
MIDI automation (CC7 volume, CC11 expression, CC10 pan). All tracks share ONE motif framework so they lock together.
Rule-based / synthetic. Style statistics per kit come from the 111 originals (epic_gen.learn)."""
import math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from epic_gen import PPQ, KITS, METERS, layout, strength, make_cell, mutate, Piece, clamp

TOMS = {0, 1, 2, 3, 4}
# section levels (planned relative energy, start->end) used for velocity level AND CC11 target
LEVELS = [(.22, .44), (.30, .70), (.55, .72), (.60, .74), (.68, .90), (.88, .97), (.34, .52), (.60, .78), (.72, .95), (.92, 1.0), (.70, .08)]
BASE7 = [112, 104, 96, 98, 108, 100, 96, 92, 88, 84]
PAN = [64, 60, 74, 50, 64, 58, 70, 38, 92, 98]
ROLES_END = {0: 'FINAL_IMPACT', 1: 'IMPACT_SUPPORT', 2: 'SINGLE_ACCENT', 3: 'RESOLVING_PHRASE', 4: 'IMPACT_SUPPORT', 5: 'IMPACT_SUPPORT',
             6: 'PRE_FINAL_FILL', 7: 'SINGLE_ACCENT', 8: 'EARLY_RELEASE', 9: 'EARLY_RELEASE'}
INTRO_STYLES = {
    'taiko-led': [(0, 0, 'impacts', 'FOUNDATION'), (1, .25, 'motif', 'RHYTHMIC_SUPPORT'), (2, .4, 'accents', 'TENSION'), (3, .6, 'motif', 'RHYTHMIC_SUPPORT'),
                  (7, .6, 'pulse', 'TEXTURE'), (8, .65, 'accents', 'TEXTURE'), (9, .85, 'subdiv', 'DETAIL'), (6, .88, 'roll', 'TRANSITION'), (4, .88, 'hit', 'ACCENT')],
    'toms-led': [(1, 0, 'pulse', 'FOUNDATION'), (0, .2, 'impacts', 'RHYTHMIC_SUPPORT'), (2, .4, 'accents', 'TENSION'), (3, .55, 'motif', 'RHYTHMIC_SUPPORT'),
                 (7, .5, 'motif', 'TEXTURE'), (9, .8, 'subdiv', 'DETAIL'), (5, .8, 'pulse', 'MARCH'), (6, .9, 'roll', 'TRANSITION')],
    'ethnic-led': [(7, 0, 'motif', 'FOUNDATION'), (8, .15, 'pulse', 'TEXTURE'), (0, .35, 'impacts', 'RHYTHMIC_SUPPORT'), (1, .5, 'motif', 'RHYTHMIC_SUPPORT'),
                   (2, .6, 'accents', 'TENSION'), (9, .75, 'subdiv', 'DETAIL'), (3, .8, 'accents', 'ACCENT'), (6, .9, 'roll', 'TRANSITION')],
    'snare-march': [(5, 0, 'pulse', 'FOUNDATION'), (0, .12, 'impacts', 'RHYTHMIC_SUPPORT'), (1, .4, 'motif', 'RHYTHMIC_SUPPORT'), (2, .55, 'accents', 'TENSION'),
                    (8, .6, 'pulse', 'TEXTURE'), (4, .85, 'hit', 'ACCENT'), (6, .9, 'roll', 'TRANSITION')],
    'war-open': [(4, 0, 'impacts', 'FOUNDATION'), (0, 0, 'impacts', 'FOUNDATION'), (1, .3, 'motif', 'RHYTHMIC_SUPPORT'), (2, .5, 'accents', 'TENSION'),
                 (7, .5, 'motif', 'TEXTURE'), (9, .8, 'subdiv', 'DETAIL'), (3, .85, 'accents', 'ACCENT'), (6, .92, 'roll', 'TRANSITION')],
}
BUILD_STYLES = ['layering', 'density', 'roll-driven', 'call-response', 'syncopation', 'break-and-impact', 'hybrid']
CLIMAX_STYLES = ['impact-driven', 'motif-driven', 'roll-driven', 'syncopated']
BREAK_STYLES = ['sparse-low-pulse', 'heartbeat-motif', 'texture-pair', 'stop-time']
OUTRO_STRATS = ['A-impact-silence', 'B-impact-decay', 'C-resolving-phrase', 'D-rolling-tail', 'E-false-stop', 'F-call-response-close', 'G-march-out', 'H-heartbeat-ritual']
GROOVE_STYLES = ['driving', 'ostinato', 'syncopated']

_W = {}
STYLE_TAB = {
 'epic_war': dict(groove=['driving', 'driving', 'ostinato'], intro=['war-open', 'taiko-led'], ib=['layered', 'rhythmic'], build=['layering', 'break-and-impact', 'density'],
                  climax=['impact-driven', 'motif-driven'], brk=['sparse-low-pulse', 'heartbeat-motif'], outro=['A-impact-silence', 'B-impact-decay', 'G-march-out'],
                  order=[0, 4, 1, 5, 2, 3, 6, 7, 8, 9], dm=1.1, lv=1.0, toff={0: 6, 4: 7, 1: 2, 8: -3, 9: -4}, secw={9: 1.25, 5: 1.1}),
 'trailer_action': dict(groove=['syncopated', 'driving'], intro=['toms-led', 'snare-march', 'war-open'], ib=['roll-driven', 'rhythmic'],
                  build=['roll-driven', 'syncopation', 'break-and-impact', 'hybrid'], climax=['roll-driven', 'syncopated', 'impact-driven'], brk=['stop-time', 'texture-pair'],
                  outro=['A-impact-silence', 'E-false-stop', 'B-impact-decay'], order=[1, 5, 2, 6, 0, 3, 9, 4, 8, 7], dm=1.15, lv=1.0, toff={2: 5, 6: 4, 9: 3, 7: -3, 0: -2}, secw={4: 1.2, 8: 1.2}),
 'dark_cinematic': dict(groove=['ostinato', 'driving'], intro=['taiko-led', 'war-open'], ib=['layered', 'rhythmic'], build=['layering', 'density', 'call-response'],
                  climax=['impact-driven', 'motif-driven'], brk=['sparse-low-pulse', 'heartbeat-motif', 'stop-time'], outro=['A-impact-silence', 'E-false-stop', 'H-heartbeat-ritual', 'D-rolling-tail'],
                  order=[0, 4, 1, 3, 7, 5, 2, 8, 6, 9], dm=0.8, lv=0.92, toff={0: 5, 4: 5, 3: 2, 2: -8, 9: -12, 8: -8, 7: 3}, secw={0: 1.2, 6: 1.2}),
 'heroic': dict(groove=['driving', 'ostinato'], intro=['taiko-led', 'toms-led'], ib=['layered', 'rhythmic'], build=['layering', 'density', 'hybrid'],
                  climax=['motif-driven', 'impact-driven'], brk=['texture-pair', 'sparse-low-pulse'], outro=['B-impact-decay', 'C-resolving-phrase', 'F-call-response-close'],
                  order=[0, 1, 5, 3, 2, 4, 6, 7, 8, 9], dm=1.0, lv=1.0, toff={1: 4, 5: 3, 3: 3, 2: 2}, secw={4: 1.3, 8: 1.3}),
 'hybrid_percussion': dict(groove=['syncopated', 'ostinato'], intro=['ethnic-led', 'toms-led'], ib=['rhythmic', 'roll-driven'], build=['syncopation', 'hybrid', 'call-response'],
                  climax=['syncopated', 'motif-driven'], brk=['texture-pair', 'stop-time', 'heartbeat-motif'], outro=['D-rolling-tail', 'F-call-response-close', 'C-resolving-phrase'],
                  order=[8, 9, 1, 5, 7, 2, 0, 3, 6, 4], dm=1.05, lv=1.0, toff={8: 5, 9: 4, 7: 3, 0: -4, 4: -4}, secw={3: 1.2}),
 'tribal_cinematic': dict(groove=['ostinato', 'syncopated'], intro=['ethnic-led'], ib=['layered', 'rhythmic'], build=['layering', 'call-response', 'syncopation'],
                  climax=['motif-driven', 'syncopated'], brk=['heartbeat-motif', 'texture-pair'], outro=['H-heartbeat-ritual', 'F-call-response-close', 'D-rolling-tail'],
                  order=[7, 8, 0, 1, 3, 9, 5, 2, 4, 6], dm=1.0, lv=1.0, toff={7: 6, 8: 5, 0: 2, 3: 3, 4: -4, 6: -3}, secw={2: 1.15, 3: 1.15}),
 'marching': dict(groove=['driving', 'ostinato'], intro=['snare-march'], ib=['rhythmic', 'layered'], build=['layering', 'density'],
                  climax=['motif-driven', 'impact-driven'], brk=['sparse-low-pulse', 'stop-time'], outro=['G-march-out', 'C-resolving-phrase', 'B-impact-decay'],
                  order=[5, 0, 1, 6, 4, 3, 2, 8, 9, 7], dm=0.95, lv=1.0, toff={5: 7, 6: 5, 0: 2, 2: -3, 8: -3}, secw={2: 1.2, 7: 1.2}),
 'tension_build': dict(groove=['ostinato', 'driving'], intro=['taiko-led', 'toms-led', 'ethnic-led'], ib=['roll-driven', 'layered'], build=['roll-driven', 'density', 'layering'],
                  climax=['roll-driven', 'impact-driven'], brk=['heartbeat-motif', 'sparse-low-pulse'], outro=['E-false-stop', 'A-impact-silence', 'D-rolling-tail'],
                  order=[0, 1, 6, 3, 5, 2, 7, 8, 9, 4], dm=1.0, lv=0.92, toff={6: 6, 3: 3}, secw={1: 1.5, 4: 1.7, 8: 1.7, 2: 0.8, 3: 0.8}),
 'battle_sequence': dict(groove=['syncopated', 'driving'], intro=['war-open', 'snare-march'], ib=['rhythmic', 'roll-driven'], build=['call-response', 'break-and-impact', 'syncopation'],
                  climax=['syncopated', 'impact-driven', 'roll-driven'], brk=['stop-time', 'texture-pair'], outro=['F-call-response-close', 'A-impact-silence', 'B-impact-decay'],
                  order=[4, 0, 2, 1, 5, 3, 6, 7, 8, 9], dm=1.1, lv=1.0, alt=True, toff={4: 5, 2: 4, 0: 2, 5: 2}, secw={5: 1.15, 9: 1.15}),
 'minimal_cinematic': dict(groove=['ostinato'], intro=['taiko-led', 'ethnic-led'], ib=['layered'], build=['layering', 'call-response'],
                  climax=['motif-driven', 'impact-driven'], brk=['sparse-low-pulse', 'stop-time'], outro=['A-impact-silence', 'E-false-stop', 'H-heartbeat-ritual'],
                  order=[0, 8, 1, 7, 3, 5, 9, 2, 4, 6], dm=0.6, lv=0.94, toff={0: 4, 2: -6, 9: -8}, secw={6: 1.4, 10: 1.4, 0: 1.3}),
}
INT_F = {1: .55, 2: .72, 3: .86, 4: 1.0, 5: 1.04}         # energy scale
INT_D = {1: .45, 2: .65, 3: .85, 4: 1.05, 5: 1.3}         # note-density scale
INT_FILL = {1: .35, 2: .6, 3: .85, 4: 1.0, 5: 1.0}        # share of gap-filler hits kept
PROFILE_HEAD = {'A': [0, 1], 'B': [1, 5], 'C': [8, 9], 'D': [0, 5], 'E': []}


def thin(rng, lay, steps, dens, keep=0.8):
    return {s for s in steps if strength(lay, s) >= keep or rng.random() < dens}


class Composer:
    def __init__(self, K, mname, groups, feel, tempo, nbs, seed, spec=None):
        self.m, self.groups, self.feel, self.tempo, self.nbs, self.seed = mname, groups, feel, tempo, nbs, seed
        self.spec = spec
        self._setup_spec()
        self.lay = layout(METERS[mname], groups, feel)
        self.bar, self.g, self.S, self.ng = self.lay['bar'], self.lay['g'], self.lay['S'], self.lay['ng']
        self.TB = sum(nbs)
        self.total = self.TB * self.bar
        self.starts = [sum(nbs[:i]) for i in range(11)]
        self.rng = random.Random(seed)
        self.Ks = [K[k] for k in KITS]
        self.P = [Piece(self.Ks[k], self.lay, feel, random.Random(seed * 131 + k), self.total) for k in range(10)]
        self.memo = [dict() for _ in range(10)]
        self.log, self.entry_plan, self.styles = [], {}, {}
        self.cc_notes = []
        self.impacts = []
        self.outro_cut = None
        r = self.rng
        ST = self.ST
        pg = ST['groove'] if ST else GROOVE_STYLES
        pb = ST['build'] if ST else BUILD_STYLES
        pc = ST['climax'] if ST else CLIMAX_STYLES
        self.styles = dict(groove=r.choice(pg), intro=r.choice(ST['intro'] if ST else list(INTRO_STYLES)), intro_build=r.choice(ST['ib'] if ST else ['rhythmic', 'layered', 'roll-driven']),
                           build_a=r.choice(pb), climax_a=r.choice(pc), breakdown=r.choice(ST['brk'] if ST else BREAK_STYLES),
                           build_b=None, final_climax=None, outro=r.choice(ST['outro'] if ST else OUTRO_STRATS))
        self.styles['build_b'] = r.choice([b for b in pb if b != self.styles['build_a']] or pb)
        self.styles['final_climax'] = r.choice([c for c in pc if c != self.styles['climax_a']] or pc)
        self.M_A = self.motif(self.styles['groove'], None)
        self.M_B = self.motif(r.choice([s for s in pg if s != self.styles['groove']] or pg) if r.random() < .6 else self.styles['groove'], self.M_A)

    # ------------------------------------------------------------ motif framework (shared by all tracks)
    def motif(self, style, parent):
        r, lay, S = self.rng, self.lay, self.S
        arch = dict(driving='pulse', ostinato='ostinato', syncopated='sync')[style]
        if parent is None:
            core = set(make_cell(r, lay, arch if arch != 'pulse' else 'gallop', self.Ks[0], 0.8))
        else:
            keep = {s for s in parent['core'] if strength(lay, s) >= 0.8}
            core = keep | set(make_cell(r, lay, arch if arch != 'pulse' else 'gallop', self.Ks[0], 0.8))
        core.add(0)
        weak = [s for s in range(S) if strength(lay, s) < 0.6 and s not in core]
        strong = [s for s in range(S) if strength(lay, s) >= 0.8]
        M = dict(style=style, core=core, strong=set(strong))
        M['t_add'] = set(r.sample(weak, min(len(weak), r.randint(1, 3)))) if weak else set()
        non_anchor = [s for s in core if strength(lay, s) < 0.8]
        M['t_rm'] = set(r.sample(non_anchor, min(len(non_anchor), r.randint(1, 2)))) if non_anchor else set()
        E = {s for s in core if strength(lay, s) < 0.9 and r.random() < 0.55}
        E |= {s + 1 for s in core if s + 1 < S and lay['j'][s + 1] != 0 and r.random() < 0.35}
        M['E'] = E | {0}
        M['E2'] = mutate(r, lay, M['E'], 0.25)
        starts, gs, ng = lay['starts'], lay['gs'], lay['ng']
        if style == 'driving':
            snare = {st for st in starts[1:]} | {st + gs[i] // 2 for i, st in enumerate(starts) if gs[i] >= 4 and r.random() < .5}
        elif style == 'ostinato':
            snare = {s for s in range(S) if lay['j'][s] % 2 == 0}
        else:
            snare = {st + gs[i] - 1 for i, st in enumerate(starts)} | set(starts[1:])
        M['snare'] = snare
        offs = [s for s in range(S) if strength(lay, s) < 0.5 and s not in core]
        M['metal'] = set(r.sample(offs, min(len(offs), max(3, S // 3)))) if offs else set()
        free = [s for s in range(S) if strength(lay, s) < 0.55 and s not in core | snare | M['metal']]
        if len(free) < 3: free = [x for x in range(S) if x not in core and x not in snare and strength(lay, x) < 0.8] or [x for x in range(1, S)]
        M['hand'] = set(r.sample(free, min(len(free), max(3, S // 3)))) if free else set()
        M['hi'] = {s for s in range(S) if lay['j'][s] % 2 == 0 and s != 0} | ({0} if r.random() < .3 else set())
        sh = gs[0]
        M['eth'] = {(s + sh) % S for s in core if r.random() < 0.75} | {starts[ng // 2]}
        M['war'] = {0, starts[ng // 2]}
        free2 = [x for x in range(S // 2, S) if strength(lay, x) < 0.8 and x not in core]
        M['ctom'] = set(r.sample(free2, min(len(free2), 3))) if free2 else {S - 1}
        M['trio'] = set(r.sample([x for x in range(1, S) if strength(lay, x) < 0.6], min(3, max(1, S // 6)))) if S > 3 else {1}
        M['pitchseed'] = r.randint(0, 10 ** 6)
        return M


    # ------------------------------------------------------------ style / intensity / activity (CueStrike-5M spec)
    def _setup_spec(self):
        sp = self.spec
        self.LV = [tuple(x) for x in LEVELS]
        self.DT = dict(self.DTAB)
        self.TOFF_ = list(self.TOFF)
        self.fm = 1.0
        self.ST = None
        self.alt = False
        self.allowed = None
        if not sp:
            return
        ST = STYLE_TAB[sp['style']]
        self.ST = ST
        I = sp['intensity']
        f, dmI, lv = INT_F[I], INT_D[I], ST['lv']
        for si in range(11):
            a, z = LEVELS[si]
            if si == 10:
                self.LV[si] = (a * (0.9 + 0.1 * f), z)
            elif si == 6:
                g = min(0.5 + 0.5 * f, 0.85 * f)
                self.LV[si] = (max(.1, a * g * lv), max(.14, z * g * lv))
            else:
                a2, z2 = max(.1, a * f * lv), max(.14, z * f * lv)
                if I == 5 and si in (2, 3, 4, 5, 7, 8, 9): a2, z2 = min(1.0, a2 + .05), min(1.0, z2 + .03)
                self.LV[si] = (min(a2, 1.0), min(z2, 1.0))
        for si in range(11):
            a, z = self.DTAB[si]
            m = dmI * ST['dm'] if si not in (6, 10) else (0.6 + 0.4 * dmI) * (0.75 + 0.25 * ST['dm'])
            self.DT[si] = (max(.1, a * m), max(.1, z * m))
        for k, d in ST['toff'].items(): self.TOFF_[k] += d
        self.fm = INT_FILL[I]
        self.alt = bool(ST.get('alt')) or sp['profile'] == 'E'
        # ---- active-track sets per section
        head = PROFILE_HEAD[sp['profile']]
        order = []
        for k in ST['order'][:1] + head + ST['order'] + list(range(10)):
            if k not in order: order.append(k)
        self.order = order
        nm = sp['n_main']
        add = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5}[I]
        n_cl = min(10, nm + add)
        n_in = max(1, min(nm, 1 + (nm >= 4) + (nm >= 7) + (nm >= 9)))
        n_ib = max(n_in, min(10, (nm + 1) // 2 + 1)) if nm > 1 else 2
        n_bu = min(10, nm + 1 + (I >= 4))
        clim = order[:n_cl]
        if sp['profile'] == 'D' and n_cl >= 3 and 4 not in clim: clim = clim[:-1] + [4]
        sets = {0: order[:n_in], 1: order[:n_ib], 2: order[:nm], 3: order[:nm], 4: order[:n_bu], 5: clim,
                6: order[:max(2, min(4, nm))], 7: order[:nm], 8: order[:n_bu], 9: clim, 10: order[:max(3, min(nm + 1, 7))]}
        if sp['profile'] == 'D' and nm >= 3: sets[10] = sorted(set(sets[10]) | {0, 4})
        self.allowed = {si: set(v) for si, v in sets.items()}

    def apply_activity(self):
        if not self.allowed: return
        bar = self.bar
        for k in range(10):
            keep = []
            for n in self.P[k].notes:
                b = int((n[0] + 15) // bar)
                si = self.sec_of_bar(b)
                if k not in self.allowed[si]: continue
                if self.alt and si in (2, 3, 7):
                    idx = self.order.index(k)
                    if idx >= 2 and idx < self.spec['n_main'] and ((b - self.starts[si]) // 4) % 2 != idx % 2: continue
                keep.append(n)
            self.P[k].notes[:] = keep
        # no dead bars: any bar left empty by the track filter gets a quiet pulse from the section's lead allowed track
        have = set()
        for k in range(10):
            for n in self.P[k].notes: have.add(int((n[0] + 15) // bar))
        for si in range(11):
            if si == 6: continue
            if si == 10 and self.styles['outro'][0] in 'EH': continue
            lead = [k for k in self.order if k in self.allowed[si]]
            if not lead: continue
            for lb in range(self.nbs[si]):
                b = self.starts[si] + lb
                if b in have or (si == 10 and b >= self.TB - 1): continue
                k = lead[lb % min(2, len(lead))]
                for s_ in self.filler(k, si, lb, self.nbs[si])[:4]:
                    self.hit(k, b, s_, self.lev(si, lb, self.nbs[si]) * (0.85 if si in (0, 10) else 1.0), key=('ag', si, k, s_), stack=0.1)
        # core tracks (Taiko, Epic Toms, Solid Snare) re-enter on the downbeat of every groove / build / climax section
        for si in (2, 3, 4, 5, 7, 8, 9):
            t0 = self.starts[si] * bar
            for k in (0, 1, 5):
                if k not in self.allowed[si]: continue
                if not any(t0 <= n[0] < t0 + 2 * self.g for n in self.P[k].notes):
                    self.hit(k, self.starts[si], 0, self.lev(si, 0, self.nbs[si]), p=self.Ks[k]['anchor'], v=100, stack=0, d=240)
        # the last bar always lands as a stacked hit (3 or more tracks) so the ending is decisive
        Lb = self.TB - 1
        pres = {k for k in range(10) for n in self.P[k].notes if abs(n[0] - Lb * bar) <= 20 and n[3] >= 105}
        for k in [x for x in self.order if x in self.allowed[10] and x not in pres][:max(0, 3 - len(pres))]:
            self.hit(k, Lb, 0, 1.0, p=self.Ks[k]['anchor'], v=118, stack=0, d=960)
        # the piece opens on the downbeat: if the section's lead track starts late, add a quiet downbeat hit
        if not any(n[0] <= 20 for k in range(10) for n in self.P[k].notes):
            k = [x for x in self.order if x in self.allowed[0]][0]
            self.hit(k, 0, 0, self.lev(0, 0, self.nbs[0]), p=self.Ks[k]['anchor'], v=96, stack=0, d=480)
        # tracks that never play anywhere get a two-hit cameo before the final outro so all ten tracks exist in the piece
        self.cameo = []
        for k in range(10):
            if not self.P[k].notes:
                b = self.TB - self.nbs[10] - 1
                for s_, v in ((0, 96), (self.lay['starts'][-1], 104)):
                    self.hit(k, b, s_, 0.9, p=self.Ks[k]['anchor'], v=v, stack=0, d=480)
                self.cameo.append(k)
                si_c = 9
                self.log_phrase(si_c, k, 'cameo', 'two-hit cameo at the end of the final climax')
                self.entry_plan.setdefault(si_c, []).append(dict(instrument=KITS[k][3:], track_id=k, entry_bar=self.nbs[si_c], role='CAMEO', activity='two-hit cameo'))
        keep_imp = []
        for kk, tt in self.impacts:
            if any(abs(n[0] - tt) <= 40 for n in self.P[kk].notes): keep_imp.append((kk, tt))
        self.impacts = keep_imp

    # ------------------------------------------------------------ low level
    def pitch(self, k, key, st, level=0.7):
        m = self.memo[k]
        if key not in m:
            m[key] = self.P[k].pick(st, level)
        return m[key]

    def vel(self, k, p, st, level, bonus=0):
        return int(clamp(self.P[k].vel_for(p, st, level) + (level - 0.65) * 46 + bonus, 36, 127))

    def hit(self, k, b, s, level, key=None, p=None, bonus=0, v=None, d=None, stack=None, exact=False):
        if b < 0 or b >= self.TB:
            return
        st = strength(self.lay, min(s, self.S - 1))
        if p is None:
            p = self.pitch(k, key if key is not None else ('x', s), st, level)
        if v is None:
            v = self.vel(k, p, st, level, bonus)
        self.P[k].add(b * self.bar + s * self.g, p, int(clamp(v, 36, 127)), d=d, exact=exact, stack_chance=stack, s_strength=st, level=level)

    def lev(self, si, lb, nb):
        a, z = self.LV[si]
        return a + (z - a) * (lb + 0.5) / nb

    def ens_hit(self, b, s, kits, level, v0=120, exact_stack=True):
        for i, k in enumerate(kits):
            K = self.Ks[k]
            ps = [K['anchor']] + ([K['accents'][0]] if K['accents'] and self.rng.random() < 0.5 else [])
            for p in ps:
                self.hit(k, b, s, level, p=p, v=int(clamp(v0 - 2 * i - self.rng.randint(0, 3), 70, 127)), stack=0, d=(480 if not K['seq'] else 480))
            if v0 >= 108: self.impacts.append((k, b * self.bar + s * self.g))

    def _sub(self, k, b, tick, p, v, d=70):
        if b < 0 or b >= self.TB or tick > self.bar - (self.g // 2 + 4): return
        tick = max(0, tick + self.rng.randint(-6, 6)) if tick > 40 else tick
        self.P[k].add(b * self.bar + tick, p, int(clamp(v, 30, 127)), d=d, exact=True, stack_chance=0, s_strength=0.3, level=0.7)

    def roll(self, k, b, s0, n, v0, v1, level=0.8):
        """a real roll: half-grid strokes (32nd feel), alternating sticking, exponential crescendo, accent on the last stroke"""
        K = self.Ks[k]
        sub = max(40, self.g // 2)
        t0 = s0 * self.g
        cnt = max(4, min(int((n * self.g) // sub), 48))
        off = self.rng.randrange(max(1, len(K['body']))) if K['body'] else 0
        for i in range(cnt):
            t = t0 + i * sub
            if t > self.bar - (self.g // 2 + 4): break
            x = i / max(1, cnt - 1)
            v = v0 + (v1 - v0) * (x ** 1.6) + self.rng.randint(-4, 4) + (6 if i % 2 == 0 else 0) + (8 if i == cnt - 1 else 0)
            if K['body']:
                p = K['body'][(off + (i % 2)) % len(K['body'])] if k not in TOMS else K['body'][(i % 2) % min(2, len(K['body']))]
            else:
                p = K['anchor']
            self._sub(k, b, t, p, v, d=sub - 8)

    def tomrun(self, k, b, s0, n, v0, v1, asc=True, level=0.8):
        """tom run on a half-grid: each drum is struck twice (16th pairs), crescendo through the run"""
        pool = sorted(self.Ks[k]['pool'])
        seq = pool if asc else pool[::-1]
        sub = max(40, self.g // 2)
        cnt = max(4, min(int(n * self.g // sub), 32))
        for i in range(cnt):
            t = s0 * self.g + i * sub
            if t > self.bar - (self.g // 2 + 4): break
            x = i / max(1, cnt - 1)
            v = v0 + (v1 - v0) * x + (5 if i % 2 == 0 else 0) + self.rng.randint(-3, 3)
            self._sub(k, b, t, seq[(i // 2) % len(seq)], v, d=sub + 30)

    def log_phrase(self, si, k, kind, detail):
        self.log.append(dict(section_index=si + 1, kit_index=k, kind=kind, detail=detail))

    # ------------------------------------------------------------ patterns for one bar of groove-like material
    DTAB = {0: (.3, .3), 1: (.45, .9), 2: (.5, .65), 3: (.6, .8), 4: (.85, 1.4), 5: (1.1, 1.25), 6: (.3, .4), 7: (.6, .75), 8: (.9, 1.45), 9: (1.2, 1.4), 10: (.25, .25)}

    def D(self, si, lb, nb):
        a, z = self.DT[si]
        return a + (z - a) * (lb + 0.5) / nb

    def bar_pattern(self, k, M, mode, ph, parity, dens, D=1.0, bi=0):
        r = random.Random(self.seed * 7 + k * 101 + ph * 13 + parity * 3 + bi * 29 + (1 if M is self.M_B else 0))
        lay, S = self.lay, self.S
        weak = [x for x in range(S) if strength(lay, x) < 0.6]

        def adj(st, keep=0.8, addp=1.1):
            if D < 1: st = thin(r, lay, st, max(0.12, D * 0.7), keep=keep)
            elif D > 1: st = set(st) | {w for w in weak if r.random() < (D - 1) * addp}
            return st
        if k == 0:
            s = set(M['core'])
            if mode == 'var': s = (s - M['t_rm']) | M['t_add']
            elif mode == 'groove' and ph == 2: s -= M['t_rm']
            elif mode in ('groove', 'climax', 'build') and ph in (1, 3): s |= M['t_add']
            if mode == 'climax': s |= M['t_add']
            s = adj(s) | {0}
        elif k == 1:
            s = set(M['E2'] if (mode in ('var', 'climax') and parity) or ph == 3 else M['E'])
            s = adj(s)
        elif k == 2:
            s = set(M['metal']) if (ph >= 1 or mode in ('var', 'climax', 'groove')) else set()
            if mode == 'var': s = mutate(r, lay, s, .3) - {0}
            if mode == 'groove' and ph == 0: s = thin(r, lay, s, .55, keep=2)
            if D > 1: s |= {w for w in weak if r.random() < (D - 1) * .5}
        elif k == 3:
            resp = M['ctom']
            s = set(resp) if (ph >= 1 or mode in ('climax', 'var', 'build')) and (parity == 1 or bi == 3 or mode in ('climax', 'build')) else set()
            if bi == 3 and ph >= 1: s |= {x for x in range(S // 2, S) if strength(lay, x) < 0.8 and r.random() < .5}
        elif k == 4:
            s = set()
            if mode == 'climax': s = set(M['war']) if parity == 0 else {0}
            elif mode == 'build': s = {0} if ph >= 2 and parity == 0 else set()
            elif ph >= 1 and bi == 0: s = {0} | ({lay['starts'][self.ng // 2]} if mode == 'var' else set())
        elif k == 5:
            s = set(M['snare'])
            if mode == 'var': s = (mutate(r, lay, s, .2) - {0}) or set(M['snare']) or {0}
            s = adj(s, keep=0.8, addp=0.8)
        elif k == 6:
            s = set()
            tail = list(range(max(1, S - max(3, S // 4)), S))
            if mode in ('climax', 'build') and (parity == 1 or bi == 3): s = {x for x in tail}
            elif mode in ('groove', 'var') and ph >= 1 and bi == 3: s = set(tail[-3:])
            elif mode == 'climax': s = set(M['trio'])
            if mode == 'climax' and parity == 0: s |= set(M['trio'])
        elif k == 7:
            s = set(M['eth']) if (ph >= 1 or mode in ('climax', 'groove', 'build')) else set()
            if D > 1: s |= {w for w in weak if r.random() < (D - 1) * .5}
        elif k == 8:
            s = set(M['hand']) if (ph >= 1 or mode in ('climax', 'groove', 'var', 'build')) else set()
            if D > 1: s |= {w for w in range(S) if lay['j'][w] % 2 == 1 and r.random() < (D - 1) * .6}
        else:
            s = set(M['hi']) if (ph >= 1 or mode in ('climax', 'build')) else (set(list(M['hi'])[::2]) if mode in ('var', 'groove') else set())
            if D > 1.1: s |= {w for w in range(S) if lay['j'][w] % 2 == 1 and r.random() < (D - 1.1) * 1.2}
        if k in (0, 1, 5) and bi in (2, 3):
            s = mutate(r, lay, s, 0.14 if bi == 2 else 0.08) | ({0} if k == 0 else set())
            if k == 5: s = s or set(M['snare'])
        if parity and k in (0, 1, 5, 7, 8):
            s = mutate(r, lay, s, 0.10) | ({0} if k == 0 else set())
        if k in (7, 8, 9) and mode != 'climax':
            s = thin(r, lay, s, 0.7 * dens + 0.2, keep=2)
        elif k not in (3, 4, 6):
            s = thin(r, lay, s, max(0.4, dens), keep=0.8) if dens < 1 else s
        return sorted(s)

    # ------------------------------------------------------------ section renderers
    def groove_like(self, si, kind, M, mode, kits_core, kits_sel, sel_from, final_fill=True):
        """4-phase (4-bar phrase) groove. kits_core play all section; kits_sel enter at phase sel_from[k]."""
        b0, nb = self.starts[si], self.nbs[si]
        for lb in range(nb):
            ph = min(3, int(lb * 4 / nb))
            first_of_ph = lb == int(math.ceil(ph * nb / 4))
            last_of_ph = lb == int(math.ceil((ph + 1) * nb / 4)) - 1
            parity = lb % 2
            lev = self.lev(si, lb, nb)
            active = list(kits_core) + [k for k in kits_sel if ph >= sel_from.get(k, 1)]
            for k in active:
                st = self.bar_pattern(k, M, mode, ph, parity, 1.0 if k in kits_core else 0.9, D=self.D(si, lb, nb), bi=lb % 4)
                if lb == 0 and mode in ('groove', 'var') and (si in (2, 7)) and k in (0, 1, 5):
                    st = sorted(set(st) | {0})
                for s in st:
                    bonus = 8 if strength(self.lay, s) >= 0.8 else 0
                    self.hit(k, b0 + lb, s, lev, key=(si, k, s, ph % 2), bonus=bonus)
            if lb == 0 and si in (2, 7):                                # clear entry statement
                self.ens_hit(b0, 0, [0, 1] + ([4] if si == 7 else []), lev, v0=114)
            if mode == 'var' and ph == 0 and lb % 2 == 0 and 4 in kits_sel:
                self.hit(4, b0 + lb, self.lay['starts'][self.ng // 2], lev, p=self.Ks[4]['anchor'], v=104, stack=0.3)
            # phrase-ending gestures (not on the last two bars: those are transition)
            if last_of_ph and ph < 3 and nb >= 4:
                self.phrase_fill(si, b0 + lb, ph, lev, kits_core, kits_sel, sel_from)
        # transition: last 2 bars
        self.transition(si, kind, b0, nb, kits_core, kits_sel)

    def phrase_fill(self, si, b, ph, lev, kc, ks, sf):
        r = self.rng
        n = max(3, self.S // 3)
        if 3 in kc or 3 in ks:
            self.tomrun(3, b, self.S - n, n, 66, 100, asc=r.random() < .5, level=lev)
        elif 1 in kc:
            self.tomrun(1, b, self.S - n, n, 66, 100, asc=True, level=lev)
        if 6 in ks and ph >= 1 and r.random() < .6:
            self.roll(6, b, self.S - max(3, n - 1), max(3, n - 1), 60, 100, lev)

    def transition(self, si, kind, b0, nb, kc, ks):
        """last bar: pickup/roll/ensemble into the next section. penultimate bar: fill."""
        r, S = self.rng, self.S
        lb = nb - 1
        lev = self.lev(si, lb, nb)
        last_g = self.lay['starts'][-1]
        choice = r.choice(['roll-pickup', 'ensemble-pickup', 'tom-run', 'accent-stop'])
        k_all = list(kc) + list(ks)
        n = max(3, S // 3)
        if choice == 'roll-pickup':
            for k in (6, 5):
                if k in k_all or k == 6:
                    self.roll(k, b0 + lb, S - n, n, 62, 112, lev)
                    break
            self.hit(0, b0 + lb, last_g, lev, p=self.Ks[0]['anchor'], v=112, stack=0)
        elif choice == 'ensemble-pickup':
            self.ens_hit(b0 + lb, last_g, [k for k in (0, 1, 4, 5) if k in k_all or k in (0, 4)], lev, v0=112)
            if 3 in k_all:
                self.tomrun(3, b0 + lb, S - n, n - 1, 70, 104, True, lev)
        elif choice == 'tom-run':
            for k in (3, 1):
                if k in k_all or k == 1:
                    self.tomrun(k, b0 + lb, S - n - 1, n + 1, 66, 108, r.random() < .5, lev)
                    break
            self.hit(0, b0 + lb, last_g, lev, p=self.Ks[0]['anchor'], v=110, stack=0)
        else:                                                          # accent then a short silence (reduction before the next section)
            self.ens_hit(b0 + lb, 0, [0, 4, 1], lev, v0=112)
        self.trans_choice = getattr(self, 'trans_choice', {})
        self.trans_choice[si] = choice
        if nb >= 3:                                                   # penultimate: fill
            b = b0 + nb - 2
            if 3 in k_all or 1 in k_all:
                self.tomrun(3 if 3 in k_all else 1, b, S - n, n, 62, 98, r.random() < .5, lev)

    # ---- intro
    def render_intro(self):
        si, nb, b0 = 0, self.nbs[0], self.starts[0]
        style = self.styles['intro']
        r, S = self.rng, self.S
        plan = []
        for (k, frac, act, role) in INTRO_STYLES[style]:
            if act == 'roll' and r.random() < .35:
                act, role = 'hit', 'ACCENT'
            e = int(frac * nb)
            e = min(e, nb - 1)
            plan.append(dict(instrument=KITS[k][3:], track_id=None, entry_bar=e + 1, role=role, activity=act, k=k))
            self.log_phrase(si, k, 'intro', f'{act}@{e + 1}')
            for lb in range(e, nb):
                lev = self.lev(si, lb, nb) + 0.04 * (1 if act == 'impacts' else 0)
                rel = lb - e
                if act == 'impacts':
                    gap = max(2, nb // 3)
                    if rel % gap == 0:
                        pitch_set = [self.Ks[k]['anchor']] + self.Ks[k]['accents'][:1]
                        v = 124 if lb == 0 else 108 - 6 * (rel // gap)
                        for i, p in enumerate(pitch_set):
                            self.hit(k, b0 + lb, 0, lev, p=p, v=v - 3 * i, stack=0, d=960)
                        self._sub(k, b0 + lb, 0 + 28, self.Ks[k]['body'][0] if self.Ks[k]['body'] else pitch_set[0], v - 20, d=240)   # flam
                        self.impacts.append((k, (b0 + lb) * self.bar))
                        ng_ = self.ng
                        for q, dv in ((1, 40), (2, 54)):                                           # decaying rebounds: the impact rings
                            if q < ng_ and lb < nb - 1:
                                self.hit(k, b0 + lb, self.lay['starts'][q], lev, p=self.Ks[k]['body'][0] if self.Ks[k]['body'] else pitch_set[0], v=max(34, v - dv), stack=0, d=480)
                    elif rel % gap == gap - 1 and lb > nb // 2:
                        self.hit(k, b0 + lb, self.lay['starts'][-1], lev, p=self.Ks[k]['body'][0], v=66 + 4 * rel, stack=0)
                elif act == 'motif':
                    cand = sorted(s for s in self.M_A['E'] if s != 0 and strength(self.lay, s) >= 0.5) or [self.lay['starts'][-1]]
                    pick = random.Random(self.seed + lb // 2 * 17 + k).sample(cand, min(len(cand), 2 + (lb > nb // 2)))
                    if rel == 0 or lb % 2 == 0:
                        pick = sorted(set(pick) | {0})
                    for s in sorted(pick):
                        self.hit(k, b0 + lb, s, lev, key=('intro', k, s))
                elif act == 'accents':
                    if rel % 2 == 0:
                        s = random.Random(self.seed + lb * 3 + k).choice([x for x in range(S) if strength(self.lay, x) in (0.5, 0.55)] or [0])
                        self.hit(k, b0 + lb, s, lev, p=self.Ks[k]['accents'][0] if self.Ks[k]['accents'] else None, bonus=6, stack=0.1, key=('ia', k))
                elif act == 'pulse':
                    for gi, st in enumerate(self.lay['starts']):
                        if gi % 2 == 0 or lb > nb // 2:
                            self.hit(k, b0 + lb, st, lev - 0.05, key=('ip', k, gi), stack=0)
                elif act == 'subdiv':
                    for s in range(0, S, 2):
                        if r.random() < 0.55:
                            self.hit(k, b0 + lb, s, lev - 0.1, key=('is', k, s), stack=0)
                elif act == 'roll' and lb == nb - 1:
                    self.roll(k, b0 + lb, S - max(4, S // 2), max(4, S // 2), 56, 104, lev)
                elif act == 'hit' and lb == nb - 1:
                    self.ens_hit(b0 + lb, self.lay['starts'][-1], [k, 0], lev, v0=104)
        # first bar must open (lead kit hit on the downbeat is guaranteed by 'impacts'/'pulse'/'motif')
        for e in plan:
            e['track_id'] = e.pop('k')
        self.entry_plan[0] = plan
        # last two bars: fill and pickup into the intro build
        nq = max(3, S // 4)
        if nb >= 3:
            self.tomrun(1, b0 + nb - 2, S - nq, nq, 54, 84, True, 0.4)
        self.tomrun(3, b0 + nb - 1, S - 2 * nq, 2 * nq, 62, 112, True, 0.5)
        self.roll(6, b0 + nb - 1, S // 2, S // 2, 50, 108, 0.5)
        self.hit(0, b0 + nb - 1, self.lay['starts'][-1], 0.4, p=self.Ks[0]['anchor'], v=104, stack=0, d=480)

    # ---- intro build
    def render_intro_build(self):
        si, nb, b0 = 1, self.nbs[1], self.starts[1]
        style = self.styles['intro_build']
        r, S, lay = self.rng, self.S, self.lay
        spec = [(0, 0), (1, 0), (5, .25), (2, .25), (3, .5), (7, .5), (8, .5), (9, .6), (6, .75), (4, .88)]
        if style == 'layered':
            spec = [(0, 0), (1, 0), (5, .15), (2, .15), (7, .3), (3, .3), (8, .4), (9, .5), (6, .7), (4, .88)]
        elif style == 'roll-driven':
            spec = [(0, 0), (1, 0), (5, .3), (2, .4), (3, .5), (6, .35), (7, .6), (8, .6), (9, .7), (4, .9)]
        plan = []
        for k, frac in spec:
            e = min(nb - 1, int(frac * nb))
            plan.append(dict(instrument=KITS[k][3:], track_id=k, entry_bar=e + 1, role=['FOUNDATION', 'RHYTHMIC_SUPPORT', 'TENSION', 'FILLS', 'ACCENT', 'DRIVE', 'ROLLS', 'TEXTURE', 'TEXTURE', 'DETAIL'][k],
                             activity=style))
            self.log_phrase(si, k, 'intro-build', f'{style}@{e + 1}')
            for lb in range(e, nb):
                ph = min(3, int(lb * 4 / nb))
                lev = self.lev(si, lb, nb)
                dens = 0.45 + 0.2 * ph if style != 'rhythmic' else 0.35 + 0.28 * ph
                st = self.bar_pattern(k, self.M_A, 'build', max(1, ph) if k in (2, 3, 7, 8, 9) else ph, lb % 2, dens, D=self.D(si, lb, nb), bi=lb % 4)
                if k in (6, 4):
                    st = []
                if k == 0:
                    st = sorted(set(st) | set(lay['starts']))
                if k == 5 and style == 'rhythmic' and ph >= 2:
                    st = sorted(set(st) | {s for s in range(S) if lay['j'][s] % 2 == 0})
                for s in st:
                    self.hit(k, b0 + lb, s, lev, key=('ib', k, s, ph % 2), bonus=6 if strength(lay, s) >= .8 else 0)
        # snare trio gestures and ensemble
        n = max(4, S // 2)
        self.roll(6, b0 + nb - 2, S - n, n, 54, 96, 0.6) if nb >= 3 else None
        self.roll(6, b0 + nb - 1, S - n - 1, n + 1, 70, 114, 0.7)
        if style == 'roll-driven':
            self.roll(3, b0 + nb - 2, S - n, n, 52, 92, 0.6)
        self.tomrun(1, b0 + nb - 1, S - n, n - 1, 72, 108, True, 0.7)
        self.ens_hit(b0 + nb - 1, lay['starts'][-1], [0, 4, 1], 0.75, v0=108)
        self.entry_plan[1] = plan

    # ---- groove sections
    def render_groove_a(self):
        self.entry_plan[2] = self.groove_entry(2, [0, 1, 5], [(3, 1), (2, 1), (7, 2), (8, 2), (9, 2), (6, 3), (4, 3)])
        self.groove_like(2, 'groove', self.M_A, 'groove', [0, 1, 5], [3, 2, 7, 8, 9, 6, 4], dict(zip([3, 2, 7, 8, 9, 6, 4], [1, 1, 2, 2, 2, 3, 3])))

    def groove_entry(self, si, core, sel):
        nb = self.nbs[si]
        plan = [dict(instrument=KITS[k][3:], track_id=k, entry_bar=1, role='CORE', activity='groove') for k in core]
        plan += [dict(instrument=KITS[k][3:], track_id=k, entry_bar=int(math.ceil(ph * nb / 4)) + 1, role='SELECTIVE', activity='groove') for k, ph in sel]
        for e in plan:
            self.log_phrase(si, e['track_id'], 'groove-core' if e['role'] == 'CORE' else 'groove-selective', self.styles['groove'] if si == 2 else 'variation')
        return plan

    def render_variation(self):
        sel = [(3, 0), (2, 1), (7, 1), (8, 1), (9, 2), (6, 3), (4, 0)]
        self.entry_plan[3] = self.groove_entry(3, [0, 1, 5], sel)
        self.groove_like(3, 'var', self.M_A, 'var', [0, 1, 5], [k for k, _ in sel], {k: p for k, p in sel})

    def render_groove_b(self):
        r = self.rng
        core = [0, 1, 5]
        extra = [2] + r.sample([3, 7, 8], 2) + [9, 6, 4]
        sel = list(zip(extra, [0, 1, 1, 2, 3, 3]))
        self.entry_plan[7] = self.groove_entry(7, core, sel)
        self.groove_like(7, 'groove', self.M_B, 'groove', core, [k for k, _ in sel], dict(sel))

    # ---- builds
    def render_build(self, si, style, M):
        b0, nb = self.starts[si], self.nbs[si]
        r, S, lay = self.rng, self.S, self.lay
        ng = self.ng
        plan = []
        entry = {'layering': {0: 0, 1: 0, 5: 0, 2: .15, 7: .3, 8: .3, 3: .45, 9: .6, 6: .65, 4: .8},
                 'density': {0: 0, 1: 0, 5: 0, 2: 0, 3: 0, 7: .25, 8: .25, 9: .5, 6: .75, 4: .8},
                 'roll-driven': {0: 0, 1: 0, 5: 0, 6: .3, 3: .25, 2: .3, 7: .5, 8: .5, 9: .6, 4: .85},
                 'call-response': {0: 0, 1: 0, 5: 0, 3: 0, 2: .2, 7: .4, 8: .4, 9: .6, 6: .7, 4: .85},
                 'syncopation': {0: 0, 1: 0, 5: 0, 2: 0, 8: .15, 7: .3, 3: .4, 9: .5, 6: .75, 4: .85},
                 'break-and-impact': {0: 0, 1: 0, 5: 0, 2: .15, 3: .3, 7: .4, 8: .4, 9: .6, 6: .7, 4: .8},
                 'hybrid': {0: 0, 1: 0, 5: 0, 2: .1, 3: .25, 7: .35, 8: .35, 9: .55, 6: .65, 4: .8}}[style]
        for k, frac in entry.items():
            e = min(nb - 1, int(frac * nb))
            plan.append(dict(instrument=KITS[k][3:], track_id=k, entry_bar=e + 1, role='CORE' if k in (0, 1, 5) else 'SELECTIVE', activity=style))
            self.log_phrase(si, k, 'build-core' if k in (0, 1, 5) else 'build-selective', style)
        for lb in range(nb):
            ph = min(3, int(lb * 4 / nb))
            lev = self.lev(si, lb, nb)
            x = (lb + 0.5) / nb
            for k, frac in entry.items():
                if lb < int(frac * nb):
                    continue
                dens = 0.5 + 0.5 * x if style in ('density', 'hybrid', 'layering') else 0.7
                st = set(self.bar_pattern(k, M, 'build', ph, lb % 2, dens, D=self.D(si, lb, nb), bi=lb % 4))
                if style == 'density' and k in (0, 1, 5):
                    if x > .5: st |= {s for s in range(S) if lay['j'][s] % 2 == 0}
                    if x > .75: st |= set(range(0, S, 1))
                if style == 'syncopation' and k in (2, 8, 3):
                    st |= {s for s in range(S) if strength(lay, s) < .5 and r.random() < .35 + .3 * x}
                if style == 'call-response' and k in (3, 1):
                    st = {s for s in st if (s // max(1, S // 2) + lb) % 2 == (0 if k == 1 else 1)} | ({0} if k == 1 else set())
                if style == 'break-and-impact' and lb >= nb - 1:
                    st = set()
                if k == 0:
                    st |= set(lay['starts'])
                if k == 5:
                    st.add(0)
                for s in sorted(st):
                    self.hit(k, b0 + lb, s, lev, key=('bu', si, k, s, ph % 2), bonus=(8 if strength(lay, s) >= .8 else 0) + int(8 * x))
        n = max(4, S // 2)
        if style in ('roll-driven', 'hybrid'):
            self.roll(6, b0 + nb - 2, 0, S, 50, 100, 0.8) if nb >= 3 else None
        if style == 'layering' or style == 'hybrid':
            self.tomrun(3, b0 + nb - 2, S - n, n, 66, 104, True, 0.8) if nb >= 3 else None
        # final bar = pickup into the next section
        lb = nb - 1
        last_g = lay['starts'][-1]
        if style == 'break-and-impact':
            self.hit(0, b0 + lb, 0, 0.8, p=self.Ks[0]['anchor'], v=104, stack=0)
            self.hit(5, b0 + lb, lay['starts'][ng // 2], 0.6, key=('bb', 5), v=70, stack=0)
            self.roll(6, b0 + lb, S - 3, 3, 60, 106, 0.7)
            self.hit(0, b0 + lb, S - 1, 0.8, p=self.Ks[0]['anchor'], v=118, stack=0)
            self.trans_choice = getattr(self, 'trans_choice', {}); self.trans_choice[si] = 'break-then-impact'
        else:
            self.roll(6, b0 + lb, S - n - 1, n + 1, 64, 118, 0.85)
            self.tomrun(3, b0 + lb, S - n, n, 70, 112, r.random() < .5, 0.85)
            self.ens_hit(b0 + lb, last_g, [0, 1, 4, 5], 0.9, v0=116)
            self.trans_choice = getattr(self, 'trans_choice', {}); self.trans_choice[si] = 'ensemble-pickup'
        self.entry_plan[si] = plan

    # ---- climax
    def render_climax(self, si, style, M, final=False):
        b0, nb = self.starts[si], self.nbs[si]
        r, S, lay, ng = self.rng, self.S, self.lay, self.ng
        kits = list(range(10))
        plan = [dict(instrument=KITS[k][3:], track_id=k, entry_bar=1 if k in (0, 1, 5, 4) else 1 + (0 if r.random() < .6 else 1),
                     role='CORE' if k in (0, 1, 5) else 'SUPPORT', activity=style) for k in kits]
        for e in plan:
            self.log_phrase(si, e['track_id'], 'climax-core' if e['role'] == 'CORE' else 'climax-selective', style)
        for lb in range(nb):
            ph = min(3 if not final else 2, int(lb * (3 if final else 4) / nb))
            lev = self.lev(si, lb, nb)
            parity = lb % 2
            for k in kits:
                if lb < plan[k]['entry_bar'] - 1:
                    continue
                mode = 'climax'
                st = self.bar_pattern(k, M, mode, 3 if ph == 2 and not final else ph, parity, 1.0, D=self.D(si, lb, nb), bi=lb % 4)
                if k == 3 and style in ('roll-driven', 'motif-driven') and lb % 2 == 1:
                    st = sorted(set(st) | {s for s in range(S // 2, S) if r.random() < .5})
                if k == 2 and style == 'syncopated':
                    st = sorted(set(st) | {s for s in range(S) if strength(lay, s) < .5 and r.random() < .3})
                if k == 9 and style == 'impact-driven':
                    st = [s for s in st if r.random() < .6]
                for s in st:
                    self.hit(k, b0 + lb, s, lev, key=('cx', si, k, s, ph % 2), bonus=(10 if strength(lay, s) >= .8 else 0) + (4 if ph == 2 else 0))
            if lb == 0:                                                # strong payoff on the downbeat
                self.ens_hit(b0, 0, [0, 1, 5, 4, 2] + ([6, 3] if final else []), lev, v0=125)
            elif lb % 4 == 0:
                self.ens_hit(b0 + lb, 0, [0, 4, 1], lev, v0=118)
            if lb % 4 == 3 and lb < nb - 1:
                n = max(3, S // 3)
                self.tomrun(3, b0 + lb, S - n, n, 70, 112, r.random() < .5, lev)
                if r.random() < .6:
                    self.roll(6, b0 + lb, S - n, n, 66, 108, lev)
            if (ph == 2 or (final and lb >= nb // 2)) and lb % 4 == 1 and style in ('impact-driven', 'syncopated'):
                self.ens_hit(b0 + lb, lay['starts'][ng // 2], [0, 4, 2], lev, v0=114)
        # ending gesture
        lb = nb - 1
        end = r.choice(['ensemble-hit', 'low-hit-cut', 'fill-into-hit', 'sudden-reduction'])
        last_g = lay['starts'][-1]
        n = max(4, S // 2)
        if final:
            end = 'fill-into-hit'
        if end == 'ensemble-hit':
            self.ens_hit(b0 + lb, last_g, [0, 1, 4, 5, 2], 1.0, v0=122)
        elif end == 'low-hit-cut':
            self.hit(0, b0 + lb, last_g, 1.0, p=self.Ks[0]['anchor'], v=125, stack=0, d=960)
        elif end == 'fill-into-hit':
            self.roll(6, b0 + lb, S - n - 1, n + 1, 70, 118, 1.0)
            self.tomrun(3, b0 + lb, S - n, n, 76, 120, False, 1.0)
            self.ens_hit(b0 + lb, last_g, [0, 1, 4, 5, 2, 3], 1.0, v0=124)
        else:
            self.ens_hit(b0 + lb, 0, [0, 4], 1.0, v0=120)
        self.trans_choice = getattr(self, 'trans_choice', {}); self.trans_choice[si] = end
        self.entry_plan[si] = plan

    # ---- breakdown: a reduced groove with its own identity, surprise events, and a smooth way in and out
    SURPRISES = ['drop-slam', 'long-swell', 'half-time', 'polyrhythm', 'metal-bell', 'cascade']

    def render_breakdown(self):
        si, nb, b0 = 6, self.nbs[6], self.starts[6]
        style = self.styles['breakdown']
        r, S, lay, ng = self.rng, self.S, self.lay, self.ng
        starts, gs = lay['starts'], lay['gs']
        M = self.M_A
        pool = list(self.SURPRISES)
        nsur = 2 if nb < 14 else 3
        chosen = r.sample(pool, nsur)
        if style == 'stop-time' and 'drop-slam' not in chosen:
            chosen[0] = 'drop-slam'
        lo, hi = max(3, int(nb * 0.30)), max(5, nb - 6)
        slots = [min(nb - 5, int(lo + (hi - lo) * (q + 0.5) / len(chosen))) for q in range(len(chosen))]
        slots = sorted(set(slots))
        chosen = chosen[:len(slots)]
        sur = {b: n for b, n in zip(slots, chosen)}
        self.styles['breakdown_surprise'] = '+'.join(f'{n}@{b + 1}' for b, n in sorted(sur.items()))
        cuts = []                                                        # (bar, from_step): everything stops for the slam
        # --- bar 0: release. The climax ring continues; a falling tom cascade carries the ear down into the reduced groove
        self.hit(0, b0, 0, 0.7, p=self.Ks[0]['anchor'], v=112, stack=0, d=960)
        if self.Ks[0]['accents']:
            self.hit(0, b0, 0, 0.7, p=self.Ks[0]['accents'][0], v=100, stack=0, d=960)
        self.hit(1, b0, 0, 0.7, key=('bk0', 1), v=100, stack=0, d=720)
        self.tomrun(1, b0, S // 2, S // 2, 96, 58, False, 0.6)
        self.tomrun(3, b0, S - max(3, S // 4), max(3, S // 4), 84, 56, False, 0.5)
        for lb in range(nb):
            x = lb / max(1, nb - 1)
            lev = self.lev(si, lb, nb)
            # Taiko
            if lb > 0:
                if style == 'heartbeat-motif':
                    self.hit(0, b0 + lb, 0, lev, p=self.Ks[0]['anchor'], stack=0, v=int(84 + 14 * x), d=480)
                    self.hit(0, b0 + lb, max(1, gs[0] // 2), lev, p=self.Ks[0]['body'][0] if self.Ks[0]['body'] else None, stack=0, v=int(64 + 12 * x), d=240)
                elif style == 'texture-pair' and lb % 2 == 1:
                    self.hit(0, b0 + lb, 0, lev, p=self.Ks[0]['anchor'], stack=0, v=int(80 + 14 * x), d=720)
                else:
                    for gi, st in enumerate(starts):
                        if style != 'stop-time' or gi % 2 == 0 or x > .7:
                            self.hit(0, b0 + lb, st, lev, key=('bkb', 0, gi), stack=0.1, d=480)
            # Epic Toms: simplified motif that changes every bar
            E = sorted(M['E'])
            if lb > 0:
                pick = [E[:3], E[1:4], E[:2] + E[-1:], E[::2]][lb % 4]
                for s_ in pick:
                    self.hit(1, b0 + lb, s_, lev - .05, key=('bkb', 1, s_), stack=0.05)
            # texture: Hand + Ethnic carry the groove between the low drums
            for k_, key_ in ((8, 'hand'), (7, 'eth')):
                st_set = sorted(M[key_])
                if lb % 2 == 1 and len(st_set) > 3: st_set = st_set[1:]
                for s_ in st_set:
                    self.hit(k_, b0 + lb, s_, lev - .1, key=('bkt', k_, s_), stack=0)
            # Hi: light ticks
            if lb > 0:
                for s_ in sorted(M['hi'])[::2]:
                    self.hit(9, b0 + lb, s_, lev - .15, key=('bkh', s_), stack=0)
            # call and response: Concert Toms answers on odd bars, Metal Toms punctuates every fourth bar
            if lb % 2 == 1 and lb > 1:
                for s_ in sorted(M['ctom']):
                    self.hit(3, b0 + lb, s_, lev, key=('bkc', s_), stack=0)
            if lb % 4 == 2 and lb > 1:
                for s_ in sorted(M['metal'])[:2]:
                    self.hit(2, b0 + lb, s_, lev, p=self.Ks[2]['accents'][0] if self.Ks[2]['accents'] else None, key=('bkm', s_), stack=0.1)
            # Solid Snare returns as a ghost pulse, then a real pulse
            if x > .30:
                for gi, st in enumerate(starts):
                    if gi % 2 == 1 or x > .75:
                        self.hit(5, b0 + lb, st, lev - .1, key=('bks', gi), stack=0, v=None)
            # --- surprise events
            ev = sur.get(lb)
            if ev == 'drop-slam' and lb + 1 < nb - 2:
                cuts.append((lb, int(S * 0.55)))
                self.ens_hit(b0 + lb + 1, 0, [0, 1, 2, 3, 5, 4], 0.9, v0=120)
                self.tomrun(3, b0 + lb + 1, S - max(3, S // 4), max(3, S // 4), 70, 96, False, 0.6)
            elif ev == 'long-swell' and lb + 2 < nb - 2:
                self.roll(6, b0 + lb, 0, S, 40, 74, 0.6)
                self.roll(6, b0 + lb + 1, 0, S, 74, 116, 0.8)
                self.roll(3, b0 + lb + 1, S // 2, S // 2, 60, 108, 0.7)
                self.ens_hit(b0 + lb + 2, 0, [0, 2, 4, 1], 0.9, v0=118)
            elif ev == 'half-time':
                for q in (0, 1):
                    if lb + q < nb - 2:
                        self.hit(0, b0 + lb + q, 0, 0.8, p=self.Ks[0]['anchor'], v=116, stack=0, d=960)
                        self.hit(0, b0 + lb + q, starts[ng // 2], 0.8, p=self.Ks[0]['anchor'], v=104, stack=0, d=720)
                        self.tomrun(1, b0 + lb + q, S - 3, 3, 88, 60, False, 0.6)
            elif ev == 'polyrhythm':
                for q in (0, 1):
                    if lb + q < nb - 2:
                        K7 = self.Ks[7]; pl = sorted(K7['pool']) or [K7['anchor']]
                        for ii in range(3 + q):
                            self._sub(7, b0 + lb + q, int(ii * self.bar / (3 + q)), pl[ii % len(pl)], 92 + (8 if ii == 0 else 0), d=300)
            elif ev == 'metal-bell':
                for q in (0, 1):
                    if lb + q < nb - 2:
                        for gi, st in enumerate(starts):
                            s_ = min(S - 1, st + max(1, gs[gi] // 2))
                            self.hit(2, b0 + lb + q, s_, 0.8, p=self.Ks[2]['accents'][0] if self.Ks[2]['accents'] else None, key=('bkbell', gi), v=100 - 6 * q, stack=0, d=480)
                            if s_ + 1 < S:
                                self.hit(2, b0 + lb + q, s_ + 1, 0.6, key=('bkbell2', gi), v=62, stack=0, d=240)
            elif ev == 'cascade':
                self.tomrun(1, b0 + lb, 0, S // 3, 104, 76, False, 0.8)
                self.tomrun(3, b0 + lb, S // 3, S // 3, 100, 70, False, 0.8)
                self.tomrun(2, b0 + lb, 2 * S // 3, S - 2 * S // 3, 96, 58, False, 0.8)
        # --- way back into Main Groove B: no silence, no hard cut; the pulse thickens and a roll climbs into the groove
        if nb >= 4:
            self.roll(6, b0 + nb - 2, 0, S, 44, 82, 0.6)
            self.roll(6, b0 + nb - 1, 0, S - 2, 82, 118, 0.8)
            self.tomrun(3, b0 + nb - 1, S - max(3, S // 3), max(3, S // 3), 74, 112, True, 0.8)
            self.tomrun(1, b0 + nb - 2, S - max(3, S // 4), max(3, S // 4), 60, 92, True, 0.6)
            self.hit(0, b0 + nb - 1, starts[-1], 0.7, p=self.Ks[0]['anchor'], v=110, stack=0, d=480)
        # --- the drop-outs: remove what plays after the cut point of the bar, so the silence is exact and short
        for (b, from_step) in cuts:
            t0, t1 = (b0 + b) * self.bar + from_step * self.g - 10, (b0 + b + 1) * self.bar - 5
            for k in range(10):
                self.P[k].notes[:] = [n for n in self.P[k].notes if not (t0 <= n[0] < t1)]
        self.trans_choice = getattr(self, 'trans_choice', {}); self.trans_choice[si] = 'roll-into-groove'
        role = {0: 'FOUNDATION', 1: 'MOTIF', 2: 'ACCENT', 3: 'RESPONSE', 4: 'IMPACT', 5: 'PULSE', 6: 'TRANSITION', 7: 'TEXTURE', 8: 'TEXTURE', 9: 'DETAIL'}
        plan = []
        for k in range(10):
            ns = [n for n in self.P[k].notes if b0 * self.bar <= n[0] < (b0 + nb) * self.bar]
            if ns:
                fb = min(int((n[0] + 15) // self.bar) for n in ns) - b0 + 1
                plan.append(dict(instrument=KITS[k][3:], track_id=k, entry_bar=fb, role=role[k], activity=style))
                self.log_phrase(si, k, 'breakdown', style)
        self.entry_plan[si] = plan

    # ---- outro (4-phase: release, reduce, prepare, final)
    def render_outro(self):
        si, nb, b0 = 10, self.nbs[10], self.starts[10]
        strat = self.styles['outro']
        fam = {'D': 'B', 'E': 'A', 'F': 'C', 'G': 'A', 'H': 'B'}.get(strat[0], strat[0])      # ending family (final-hit design)
        r, S, lay, ng = self.rng, self.S, self.lay, self.ng
        last = nb - 1
        roles = dict(ROLES_END)
        for k in (2, 7):
            roles[k] = r.choice(['SINGLE_ACCENT', 'SILENT_ENDING'])
        roles[3] = r.choice(['RESOLVING_PHRASE', 'PRE_FINAL_FILL'])
        if fam == 'C':
            roles.update({1: 'RESOLVING_PHRASE', 5: 'RESOLVING_PHRASE'})
        if fam == 'A':
            roles[6] = 'EARLY_RELEASE'
        late = r.random() < 0.3                                          # final hit on the last group instead of the downbeat
        fs = lay['starts'][-1] if late else 0
        # phase bars
        def pb(frac):
            return min(last, int(round(frac * last))) if nb > 1 else 0
        b_release, b_reduce, b_prep = 0, pb(1 / 3), pb(2 / 3)
        # release: response to the final climax
        lev = self.LV[10][0]
        self.ens_hit(b0, 0, [0, 1, 5], lev, v0=112)
        for s in sorted(self.M_A['E'])[:4]:
            self.hit(1, b0, s, lev, key=('ou', 1, s), stack=0)
        for s in sorted(self.M_A['snare'])[:3]:
            self.hit(5, b0, s, lev, key=('ou', 5, s), stack=0)
        if roles[3] != 'SILENT_ENDING':
            self.tomrun(3, b0, S - 4, 4, 70, 92, False, lev)
        for k in (7, 8, 9):
            if k != 9 or True:
                for s in sorted(self.M_A['hand' if k == 8 else ('eth' if k == 7 else 'hi')])[:3]:
                    self.hit(k, b0, s, lev - .1, key=('ou', k, s), stack=0)
        # reduce
        for b in range(1, last):
            x = b / max(1, last)
            lv = lev * (1 - 0.6 * x)
            self.hit(0, b0 + b, 0, lv, p=self.Ks[0]['anchor'], v=int(100 - 30 * x), stack=0, d=960)
            if fam == 'C' or x < .6:
                for s in sorted(self.M_A['E'])[:max(1, 3 - b)]:
                    self.hit(1, b0 + b, s, lv, key=('ou', 1, s), stack=0, v=int(84 - 24 * x))
        if strat[0] in 'DEFGH':
            self.outro_mid(strat, b0, nb, last, lev)
        # prepare: a pre-final roll must come BEFORE the final hit
        n = max(3, S // 3)
        if roles[6] == 'PRE_FINAL_FILL' and (fam in 'BC' or r.random() < .5):
            if late:
                s0 = max(0, fs - n)
                self.roll(6, b0 + last, s0, fs - s0, 60, 108, 0.6) if fs - s0 >= 2 else None
            elif last >= 1:
                self.roll(6, b0 + last - 1, S - n - 1, n + 1, 60, 108, 0.6)
        # final hit (last bar)
        kits_final = [k for k in range(10) if roles[k] in ('FINAL_IMPACT', 'IMPACT_SUPPORT')]
        if fam == 'A':
            kits_final = [0, 1, 4] + ([5] if r.random() < .5 else [])
        elif fam == 'C':
            kits_final = [0, 1, 5]
        for i, k in enumerate(dict.fromkeys(kits_final)):
            K = self.Ks[k]
            for p in [K['anchor']] + (K['accents'][:1] if fam == 'B' else []):
                self.hit(k, b0 + last, fs, 0.9, p=p, v=int(clamp(124 - 3 * i - r.randint(0, 2), 100, 127)), stack=0, d=(self.bar - fs * self.g - 30 if fam == 'B' else 720))
        if fam == 'C':
            for s in sorted(self.M_A['E'])[:3]:
                self.hit(3, b0 + last, s, 0.6, key=('oc', 3), v=82, stack=0) if s < fs else None
        for k in (2, 7):
            if roles[k] == 'SINGLE_ACCENT':
                self.hit(k, b0 + last, fs, 0.8, p=self.Ks[k]['accents'][0] if self.Ks[k]['accents'] else self.Ks[k]['anchor'], v=104, stack=0, d=720)
        self.outro_roles = {TRKID: roles[k] for k, TRKID in enumerate(range(10))}
        self.outro_info = dict(strategy=strat, final_hit_step=fs, final_hit_position='last group' if late else 'downbeat')
        self.entry_plan[si] = [dict(instrument=KITS[k][3:], track_id=k, entry_bar=1, role=roles[k], activity='outro') for k in range(10)]
        for k in range(10):
            if any(n[0] >= b0 * self.bar for n in self.P[k].notes):
                self.log_phrase(si, k, 'outro', f'{strat}:{roles[k]}')

    def outro_mid(self, strat, b0, nb, last, lev):
        r, S, lay, ng = self.rng, self.S, self.lay, self.ng
        starts, gs = lay['starts'], lay['gs']
        M = self.M_A
        for b in range(1, last):
            x = b / max(1, last)
            lv = lev * (1 - 0.5 * x)
            if strat[0] == 'D':                                        # rolling tail: roll swells that get quieter, Taiko rings, falling toms
                self.hit(0, b0 + b, 0, lv, p=self.Ks[0]['anchor'], v=int(104 - 36 * x), stack=0, d=960)
                if b % 2 == 1:
                    self.roll(6, b0 + b, S // 4, S - S // 4, int(70 - 24 * x), int(100 - 44 * x), lv)
                if b % 2 == 0:
                    self.tomrun(3, b0 + b, S - max(4, S // 3), max(4, S // 3), int(100 - 30 * x), int(70 - 20 * x), False, lv)
            elif strat[0] == 'E':                                      # false stop: a driving march that stops dead, then the stinger
                for gi, st in enumerate(starts):
                    self.hit(5, b0 + b, st, lv, key=('oe', 5, gi), stack=0)
                for s_ in sorted(M['E'])[:4]:
                    self.hit(1, b0 + b, s_, lv, key=('oe', 1, s_), stack=0)
                self.hit(0, b0 + b, 0, lv, p=self.Ks[0]['anchor'], v=104, stack=0, d=480)
                if b % 2 == 0: self.ens_hit(b0 + b, 0, [0, 4, 2], lv, v0=108)
            elif strat[0] == 'F':                                      # call and response
                if b % 2 == 1:
                    self.ens_hit(b0 + b, 0, [0, 1], lv, v0=106)
                    for s_ in sorted(M['E'])[:4]: self.hit(1, b0 + b, s_, lv, key=('of', 1, s_), stack=0)
                    for gi, st in enumerate(starts): self.hit(5, b0 + b, st, lv, key=('of', 5, gi), stack=0)
                else:
                    for s_ in sorted(M['metal']): self.hit(2, b0 + b, s_, lv, key=('of', 2, s_), stack=0)
                    self.tomrun(3, b0 + b, S // 2, S // 2, 96, 64, False, lv)
                    for s_ in sorted(M['hand']): self.hit(8, b0 + b, s_, lv - .1, key=('of', 8, s_), stack=0)
            elif strat[0] == 'G':                                      # march out
                for s_ in sorted(set(starts) | {st + gs[i] // 2 for i, st in enumerate(starts) if gs[i] >= 4}):
                    self.hit(5, b0 + b, s_, lv, key=('og', 5, s_), stack=0)
                for gi, st in enumerate(starts):
                    if gi % 2 == 0: self.hit(0, b0 + b, st, lv, p=self.Ks[0]['anchor'], v=96, stack=0, d=480)
                if b % 2 == 1: self.ens_hit(b0 + b, 0, [0, 4, 1], lv, v0=108 - int(14 * x))
            else:                                                      # H: ritual heartbeat, the gaps get longer
                gap = 1 + int(2.2 * x)
                if b % gap == 0:
                    self.hit(0, b0 + b, 0, lv, p=self.Ks[0]['anchor'], v=int(110 - 24 * x), stack=0, d=1200)
                    self.hit(0, b0 + b, max(1, gs[0] // 2), lv, p=self.Ks[0]['body'][0] if self.Ks[0]['body'] else None, v=int(80 - 20 * x), stack=0, d=480)
                    self.hit(1, b0 + b, starts[ng // 2], lv, key=('oh', 1), v=int(78 - 18 * x), stack=0, d=720)
                if b % 2 == 1:
                    for s_ in sorted(M['eth'])[:3]: self.hit(7, b0 + b, s_, lv - .1, key=('oh', 7, s_), stack=0)
        if strat[0] == 'E' and nb >= 4:
            self.outro_cut = (b0 + last - 1, max(1, S // 4))

    # ------------------------------------------------------------ automation (CC7 / CC11 / CC10)
    # ------------------------------------------------------------ dynamics: absolute intensity per bar (velocity re-mapping)
    TOFF = [3, 1, -3, 0, 4, 2, -2, -8, -12, -14]

    def sec_of_bar(self, b):
        return max(i for i in range(11) if self.starts[i] <= min(b, self.TB - 1))

    def e_at(self, tick):
        """planned relative energy at a tick: section plan (linear in the section) + 4-bar phrase swell + last-bar lift in builds"""
        bf = tick / self.bar
        si = self.sec_of_bar(int(bf)); nb = self.nbs[si]
        lb = bf - self.starts[si]
        a, z = self.LV[si]
        e = a + (z - a) * min(1.0, lb / max(1, nb))
        if si == 6:                                   # smooth way down from the climax and back up into the groove (no step)
            ramp = 2.5
            if lb < ramp:
                w = 0.5 - 0.5 * math.cos(math.pi * lb / ramp)
                e = 0.83 * self.LV[5][1] * (1 - w) + e * w
            elif lb > nb - ramp:
                w = 0.5 - 0.5 * math.cos(math.pi * (lb - (nb - ramp)) / ramp)
                e = e * (1 - w) + 1.07 * self.LV[7][0] * w
        elif si == 10 and lb < 1.5:
            w = 0.5 - 0.5 * math.cos(math.pi * lb / 1.5)
            e = 0.9 * self.LV[9][1] * (1 - w) + e * w
        if si in (2, 3, 5, 7, 9):
            e += 0.05 * (((lb % 4) / 4.0) - 0.5)
        if si in (1, 4, 8) and lb >= nb - 1:
            e += 0.06 * (lb - (nb - 1))
        return max(0.03, min(1.0, e))

    def dynamics(self):
        for k in range(10):
            ns = self.P[k].notes
            if not ns: continue
            acc = {}
            for n in ns:
                si = self.sec_of_bar(int((n[0] + 15) // self.bar))
                acc.setdefault(si, []).append(n[3])
            mu = {si: sum(v) / len(v) for si, v in acc.items()}
            for n in ns:
                si = self.sec_of_bar(int((n[0] + 15) // self.bar))
                rel = max(-30, min(24, (n[3] - mu[si]) * 1.2))
                V = 46 + 70 * self.e_at(n[0])
                o = n[3]
                n[3] = int(max(28, min(127, round(V + self.TOFF_[k] + rel))))
                if (n[0] + 15) // self.bar >= self.TB - 1 and o >= 112:     # the final hit stays decisive whatever the outro level is
                    n[3] = max(n[3], min(127, o - 6))
        # the final hit and the climax downbeats stay decisive
        for k in range(10):
            for n in self.P[k].notes:
                if n[0] >= (self.TB - self.nbs[10]) * self.bar and n[3] > 0:
                    pass

    # ------------------------------------------------------------ MIDI CC automation (per track, curve-shaped, sampled at beat groups)
    def automation(self):
        r = random.Random(self.seed + 99)
        lay, bar = self.lay, self.bar
        starts = lay['starts']
        lift = r.sample([2, 3, 7, 8, 9], 2)
        sway = [7, 8, 9]
        meta = dict(cc7='per-track mix level: lifted layers rise through builds, supporting tracks ease back in climaxes, staged fade-out per track in the outro',
                    cc11='expression: planned section energy + 4-bar phrase swells + fade-in at each track entry + crescendo/diminuendo ramps on rolls + dip-and-snap before impacts + staged outro diminuendo',
                    cc10='fixed position per instrument; supporting tracks (Ethnic, Hand, Hi) drift a few steps in the grooves and climaxes and return to base',
                    lifted_layers=[KITS[k][3:] for k in lift])
        ccs = [[] for _ in range(10)]
        for k in range(10):
            ev = {}                                      # (cc, tick) -> value
            def put(cc, t, v): ev[(cc, max(0, int(t)))] = int(max(0, min(127, round(v))))
            put(10, 0, PAN[k]); put(7, 0, BASE7[k])
            notes = sorted(self.P[k].notes)
            bars_with = sorted({int((n[0] + 15) // bar) for n in notes})
            # --- CC11 base curve
            tr11 = [4, 2, -2, 0, 4, 2, -2, -4, -6, -8][k]
            for b in range(self.TB):
                si = self.sec_of_bar(b)
                for gi, st in enumerate(starts):
                    t = b * bar + st * self.g
                    e = self.e_at(t)
                    v = 36 + 90 * (e ** 1.15) + tr11
                    put(11, t, v)
            # --- swell into, and decay out of, every impact on this track (reverse-swell feel)
            def b11(t): return 36 + 90 * (self.e_at(t) ** 1.15) + tr11
            for (kk, tt) in self.impacts:
                if kk != k: continue
                bs = b11(tt)
                fdip = 0.35 if self.sec_of_bar(int(tt // bar)) in (1, 4, 8) else 1.0
                for dt, dv in ((-960, -26), (-480, -16), (-120, -6), (0, 4), (480, -6), (960, -12), (1920, 0)):
                    put(11, tt + dt, bs + (dv * fdip if dt < 0 else dv))
            # --- fade-in at track entries (first note of each section run)
            firstb = {}
            for b in bars_with:
                si = self.sec_of_bar(b)
                firstb.setdefault(si, b)
            for si, b in firstb.items():
                if si in (0, 1, 2, 3) and b > self.starts[si] and b >= 1:
                    base = ev.get((11, b * bar), 80)
                    for gi, st in enumerate(starts):
                        t = (b - 1) * bar + st * self.g
                        put(11, t, base - 34 + 34 * (gi + 1) / (len(starts) + 1))
            # --- roll / run crescendo (same run rule as the annotator)
            dist = []
            for n in notes:
                if not dist or n[0] - dist[-1][0] > 14: dist.append(n)
            i2 = 0
            while i2 < len(dist):
                j2 = i2
                while j2 + 1 < len(dist) and dist[j2 + 1][0] - dist[j2][0] <= 1.35 * self.g and int(dist[j2 + 1][0] // bar) == int(dist[i2][0] // bar): j2 += 1
                L = j2 - i2 + 1
                if L >= 4:
                    run = dist[i2:j2 + 1]
                    dv = run[-1][3] - run[0][3]
                    t0 = run[0][0]; base = ev.get((11, (t0 // self.g) * self.g), None)
                    base = base if base is not None else 92
                    for q, n in enumerate(run):
                        x = q / max(1, L - 1)
                        if dv >= 10: put(11, n[0], min(127, base - 10 + 20 * x))
                        elif dv <= -10: put(11, n[0], base + 8 - 20 * x)
                i2 = j2 + 1
            # --- dip-and-snap before section impacts (last group of builds / intro build / breakdown)
            for si in (1, 4, 8):
                b = self.starts[si] + self.nbs[si] - 1
                t_dip = b * bar + starts[-1] * self.g
                put(11, t_dip, ev.get((11, t_dip), 90) - 18)
                put(11, (b + 1) * bar, 38 + 90 * (self.e_at((b + 1) * bar + 5) ** 1.15) + tr11 + 4 if b + 1 < self.TB else 100)
            # --- outro: staged diminuendo, decisive final bar
            nb = self.nbs[10]; b0 = self.starts[10]
            role = getattr(self, 'outro_roles', {}).get(k, 'EARLY_RELEASE')
            end_b = self.TB - 1
            for b in range(b0, self.TB):
                x = (b - b0) / max(1, nb - 1)
                for gi, st in enumerate(starts):
                    t = b * bar + st * self.g
                    if b == end_b:
                        v = 118 if role in ('FINAL_IMPACT', 'IMPACT_SUPPORT') else (96 if role in ('SINGLE_ACCENT', 'RESOLVING_PHRASE', 'PRE_FINAL_FILL') else 60)
                    else:
                        fade = {'EARLY_RELEASE': 0.9, 'SILENT_ENDING': 0.9, 'SINGLE_ACCENT': 0.55, 'PRE_FINAL_FILL': 0.45, 'RESOLVING_PHRASE': 0.4}.get(role, 0.3)
                        v = (36 + 90 * (self.e_at(t) ** 1.15) + tr11) - 70 * fade * x * 0.8
                    put(11, t, v)
            # --- CC7 mix movement
            for b in range(self.TB):
                si = self.sec_of_bar(b); lb = b - self.starts[si]; nbs_ = self.nbs[si]; x = lb / max(1, nbs_ - 1)
                mod = 0
                if si == 0 and k in (7, 8, 9, 2): mod = -10
                if si in (1, 4, 8) and k in lift: mod = 14 * x
                if si in (5, 9) and k in (7, 8, 9): mod = -5
                if si in (5, 9) and k in (0, 1, 5, 4): mod = 4
                if si == 10:
                    tot = {0: 6, 1: 14, 5: 14, 4: 12}.get(k, 40 if k in (7, 8, 9) else 24)
                    mod = -tot * x * (0.6 if self.outro_roles.get(k) in ('FINAL_IMPACT', 'IMPACT_SUPPORT') else 1.0) if hasattr(self, 'outro_roles') else -tot * x
                for gi in ([0, len(starts) // 2] if si in (1, 4, 8, 10) else [0]):
                    put(7, b * bar + starts[gi] * self.g, BASE7[k] + mod)
            # --- CC10 gentle drift on supporting tracks
            if k in sway:
                for b in range(self.TB):
                    si = self.sec_of_bar(b); lb = b - self.starts[si]
                    amp = 10 if si in (2, 3, 5, 7, 9) else 0
                    put(10, b * bar, PAN[k] + amp * math.sin(2 * math.pi * (lb / 8.0) + k))
                for si in range(11):
                    put(10, self.starts[si] * bar + 1 if False else self.starts[si] * bar, PAN[k])
            # --- compress: drop redundant events (<2 change on same cc) and write out in tick order
            out = []
            for cc in (7, 10, 11):
                last = None
                for (c, t), v in sorted((kv for kv in ev.items() if kv[0][0] == cc), key=lambda z: z[0][1]):
                    if last is None or abs(v - last) >= 2 or t == 0:
                        out.append((t, cc, v)); last = v
            out.sort(key=lambda z: (z[0], z[1]))
            ccs[k] = [(t, cc, v) for t, cc, v in out]
        return ccs, meta

    # ------------------------------------------------------------ no dead bars: every active track keeps playing through its section
    def filler(self, k, si, lb, nb):
        M = self.M_B if si >= 7 else self.M_A
        lay, S = self.lay, self.S
        starts = lay['starts']
        E = sorted(M['E'])
        rr = random.Random(self.seed * 31 + si * 7 + k * 3 + lb)
        if k == 0: return sorted(set(starts) | {0}) if si not in (0, 10) else sorted({0, starts[len(starts) // 2]})
        if k == 1: return sorted(set(E[:3]) | {0}) if lb % 2 == 0 else sorted(set(E[1:4]) | {starts[len(starts) // 2]})
        if k == 2: return sorted(M['metal'])[:3 if lb % 2 else 4]
        if k == 3: return sorted(M['ctom']) if lb % 2 else sorted(M['ctom'])[:2] + [starts[-1]]
        if k == 4: return [0] if lb % 2 == 0 else [starts[len(starts) // 2]]
        if k == 5: return sorted(set(M['snare']) if si not in (0, 10) else set(starts[1:]))[:6]
        if k == 6: return sorted(range(max(1, S - 3), S)) if lb % 2 else [max(1, S // 2), max(2, S - 2)]
        if k == 7: return sorted(M['eth'])[:4]
        if k == 8: return sorted(M['hand'])[:4]
        return sorted(M['hi'])[:6 if lb % 2 else 8]

    def fill_gaps(self):
        S, lay = self.S, self.lay
        for si in range(11):
            if si == 6: continue
            nb, b0 = self.nbs[si], self.starts[si]
            for k in range(10):
                have = sorted({int((n[0] + 15) // self.bar) - b0 for n in self.P[k].notes if b0 <= int((n[0] + 15) // self.bar) < b0 + nb})
                if si == 10:
                    if self.styles['outro'][0] == 'H' and k in (0, 1, 5): continue        # ritual heartbeat: the gaps are the point
                    if k in (7, 8, 9): last_bar = max(0, nb // 2 - 1)
                    else: last_bar = nb - 2
                    if not have and k not in (0, 1, 5): continue
                    first = have[0] if have else 0
                    rng_ = range(first, last_bar + 1)
                elif si == 0:
                    ent = {1: 1, 2: 2, 3: 3, 7: 3, 8: 4, 9: 5, 5: nb // 2}
                    if k in (4, 6): continue
                    if k in ent: first = min(have[0], ent[k]) if have else ent[k]
                    elif have: first = have[0]
                    else: continue
                    rng_ = range(first, nb)
                elif si == 1:
                    ent = {5: 1, 2: 1, 3: 2, 7: 2, 8: 2, 9: 3}
                    if k in ent: first = min(have[0], ent[k]) if have else ent[k]
                    elif have: first = have[0]
                    else: continue
                    rng_ = range(first, nb)
                else:
                    if not have and k not in (2, 3, 7, 8, 9, 4, 6): continue
                    first = 0 if (k in (2, 3, 7, 8, 9, 4, 6) and si in (2, 3, 4, 7, 8)) else (have[0] if have else 0)
                    rng_ = range(first, nb)
                for lb in rng_:
                    if lb in have: continue
                    if k in (4, 6) and si not in (4, 5, 8, 9) and lb % 2 == 1: continue
                    lev = self.lev(si, lb, nb)
                    fl_ = self.filler(k, si, lb, nb)
                    if self.fm < 1: fl_ = fl_[:max(1, int(round(len(fl_) * self.fm)))]
                    for s_ in fl_:
                        self.hit(k, b0 + lb, s_, lev * (0.85 if si in (0, 10) else 1.0), key=('fg', si, k, s_), stack=0.1)
        # outro: the reduction is still a performance - a crescendo roll and a tom fill lead into the final hit
        nb, b0 = self.nbs[10], self.starts[10]
        if nb >= 3 and self.styles['outro'][0] in 'ABDGH':
            self.roll(6, b0 + nb - 2, 0, S, 50, 112, 0.6)
            if nb >= 4: self.tomrun(3, b0 + nb - 3, S - max(4, S // 2), max(4, S // 2), 60, 104, False, 0.5)
        # false stop: everything stops dead in the bar before the stinger
        if self.outro_cut is not None:
            bcut, fst = self.outro_cut
            t0, t1 = bcut * self.bar + fst * self.g - 10, (bcut + 1) * self.bar - 5
            for k in range(10):
                self.P[k].notes[:] = [n for n in self.P[k].notes if not (t0 <= n[0] < t1)]
            self.ens_hit(self.TB - 1, 0, [0, 1, 2, 3, 4, 5], 1.0, v0=124)
        # intro: opening ensemble impact and two long swelling rolls (quiet -> loud over two bars)
        nbi, bi0 = self.nbs[0], self.starts[0]
        self.ens_hit(bi0, 0, [0, 1, 4], 0.4, v0=116)
        for q, (va, vb) in ((nbi // 3, (34, 70)), (2 * nbi // 3, (46, 96))):
            if q + 1 < nbi - 2:
                self.roll(6, bi0 + q, 0, S, va, (va + vb) // 2, 0.4)
                self.roll(6, bi0 + q + 1, 0, S, (va + vb) // 2, vb, 0.4)
                self.roll(3, bi0 + q + 1, S // 2, S // 2, va + 10, vb - 4, 0.4)
        # builds: the last two bars are a full roll that climbs (not a half-bar gesture)
        for si in (1, 4, 8):
            nb_, b_ = self.nbs[si], self.starts[si]
            if nb_ >= 4:
                self.roll(6, b_ + nb_ - 2, 0, S, 52, 86, 0.7)
                self.roll(6, b_ + nb_ - 1, 0, S - 2, 84, 122, 0.9)
        # eight-bar phrase ends in grooves / variation / climax: a full-bar roll plus a tom cascade
        for si in (2, 3, 5, 7, 9):
            nb_, b_ = self.nbs[si], self.starts[si]
            for lb in range(7, nb_ - 2, 8):
                self.roll(6, b_ + lb, 0, S, 58, 108, 0.8)
                self.tomrun(1, b_ + lb, S - max(4, S // 2), max(4, S // 2), 66, 112, False, 0.8)
                self.tomrun(3, b_ + lb, S - max(4, S // 3), max(4, S // 3), 70, 114, True, 0.8)
        # groove sections: a phrase-start ensemble accent every four bars (not only in climaxes)
        for si in (2, 3, 7):
            for lb in range(4, self.nbs[si], 4):
                self.ens_hit(self.starts[si] + lb, 0, [0, 1, 5, 4], self.lev(si, lb, self.nbs[si]), v0=110)

    def render(self):
        self.render_intro()
        self.render_intro_build()
        self.render_groove_a()
        self.render_variation()
        self.render_build(4, self.styles['build_a'], self.M_A)
        self.render_climax(5, self.styles['climax_a'], self.M_A)
        self.render_breakdown()
        self.render_groove_b()
        self.render_build(8, self.styles['build_b'], self.M_B)
        self.render_climax(9, self.styles['final_climax'], self.M_B, final=True)
        self.render_outro()
        self.fill_gaps()
        self.apply_activity()
        self.dynamics()
        self.reconcile()
        return self

    def reconcile(self):
        # the plan/log must describe what is actually played: drop planned-but-silent tracks, set selective entry bars to the real first-note bar
        first = {}
        for k in range(10):
            for n in self.P[k].notes:
                b = int((n[0] + 15) // self.bar)
                si = max(i for i in range(11) if self.starts[i] <= b)
                first.setdefault((si, k), b - self.starts[si] + 1)
                first[(si, k)] = min(first[(si, k)], b - self.starts[si] + 1)
        have = {(e['section_index'] - 1, e['kit_index']) for e in self.log}
        for (si_, k_), f_ in sorted(first.items()):
            if (si_, k_) not in have:
                self.log.append(dict(section_index=si_ + 1, kit_index=k_, kind='support-fill', detail='keeps playing through the section'))
                self.entry_plan.setdefault(si_, []).append(dict(instrument=KITS[k_][3:], track_id=k_, entry_bar=f_, role='SUPPORT', activity='continuous support'))
        self.log = [e for e in self.log if (e['section_index'] - 1, e['kit_index']) in first and not (self.allowed and e['kit_index'] not in self.allowed[e['section_index'] - 1] and e['kit_index'] not in self.cameo)]
        for si, plan in list(self.entry_plan.items()):
            keep = []
            for e in plan:
                f = first.get((si, e['track_id']))
                if f is None: continue
                if self.allowed and e['track_id'] not in self.allowed[si] and e['track_id'] not in self.cameo: continue
                if e['role'] != 'CORE': e = dict(e, entry_bar=f)
                keep.append(e)
            self.entry_plan[si] = keep
