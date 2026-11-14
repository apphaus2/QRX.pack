"""Scrub: thickets, heath and thorn: dry, tangled and sunlit.

A soft backdrop, not a portrait. Day is warm, dry air moving low over the brush: less body than under trees (no
canopy to roar) and a soft, dry rustle of small leaves and stems a little higher than the forest's crowns, with one
cicada far off, a thread under it all. Night is cool and still: low air, a faint breath through the brush, and tree
crickets far away, trilling lower and longer than the forest's chirping ones. Anything you could pick out as one
thing is a cue, and cues are rare (under one a minute) and mostly far; the hero by day is a quail, by night a
nightjar-like whistle.
"""
import math

from lib import *


def pulsed(x, hz, sharp=2.0):
    """x times a pulse train of about `hz` pulses a second, a whole number of pulses over x, so a bed stays a
    loop (memoryless, so it is seamless however the loop runs). The toolkit has no amplitude-pulse modulator."""
    cycles = max(1, round(hz * len(x) / RATE))
    w = 2 * math.pi * cycles / len(x)
    return [v * (0.5 + 0.5 * math.sin(w * i)) ** sharp for i, v in enumerate(x)]


def day(s):
    # The wind's shape: a slow wandering (a new level about every 5 s) with small gusts, shallow (about 4 dB) and
    # over a floor, as the forest's.
    calm = drift(s.rng("wind"), s.seconds, every=5.0, lo=0.0, hi=0.45)
    g = gusts(s.rng("gusts"), s.seconds, count=8, rise=(2.5, 4.5), fall=(3.5, 7.0), size=(0.06, 0.14))
    wind = [0.6 + 0.4 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.5))]

    # Air low over open ground: a lighter body than the forest's.
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("body-" + side), corner=110), scale(wind, 160, 380)), wind)
                    for side in "ab"], width=0.6)

    # The brush: pink noise from 400 Hz up to 1.1 to 2 kHz, a little higher and thinner than the forest's crowns
    # (its dryness), but kept under the hiss the first version had.
    brush = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("brush-" + side)), scale(wind, 1100, 2000)), 400),
                           wind) for side in "ab"], width=0.85)

    # Small dry leaves and stems: soft puffs from 1 to about 4 kHz, thicker where the wind is up, never stopping.
    stem = lambda r: noise_burst(r, r.uniform(0.006, 0.02), lo=1000, hi=r.uniform(2800, 4200), attack=0.002,
                                 release=0.008)
    stems = scatter(s.n, s.rng("stems"), 4000, stem, level=(-8, 0), pan=(-1, 1),
                    follow=[0.4 + 0.6 * w for w in smooth(wind, 2.0)], depth=1.0)

    # One cicada far off: a narrow band at about 4.5 kHz, buzzing, fading in and out on a slow drift. A thread,
    # far under the rest.
    r = s.rng("cicada")
    buzz = pulsed(bandpass(white(s.n, r), 4400, q=4.0), 120, sharp=2.0)
    here = drift(r, s.seconds, every=8.0, lo=0.5, hi=1.0)
    cicada = stereo(apply(buzz, here), apply(pulsed(bandpass(white(s.n, r), 4400, q=4.0), 120, 2.0), here), 0.5)

    return mix((body, -8), (brush, 0), (stems, -12), (cicada, -21))


def night(s):
    # Cool still air: a low body that barely moves, and a faint breath through the brush in the middle band.
    calm = drift(s.rng("calm"), s.seconds, every=6.5, lo=0.6, hi=0.85)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=70), scale(calm, 130, 240)), calm)
                   for side in "ab"], width=0.6)
    breath = stereo(*[apply(highpass(lowpass(pink(s.n, s.rng("breath-" + side)), 1100), 300), calm)
                      for side in "ab"], width=0.8)

    # Tree crickets far away: each a trill of half a second to a second at 2.4 to 3 kHz, pulsing 35 to 50 times a
    # second, all distant and dulled. A faint presence under the air, not the body of the bed.
    def cricket(r):
        hz, rate = r.uniform(2400, 3000), r.uniform(35, 50)
        count = int(r.uniform(0.5, 1.0) * rate)
        call = trill(r, count=count, hz=hz, each=0.55 / rate, gap=0.45 / rate)
        call = distant(call, r.uniform(0.6, 0.9))
        return lambda r2: gain(call, r2.uniform(-2, 0))
    crickets = chorus(s.n, s.rng("crickets"), voices=24, voice=cricket, rate=(0.45, 0.9), jitter=0.1,
                      level=(-8, 0), pan=(-0.9, 0.9), presence=(0.2, 1.0), every=6.0)

    return mix((air, -3), (breath, -5), (crickets, -11))


def cues(s):
    # Rare and mostly far (README, "Cues are rare"): each bed's hero every 90 to 240 s, the rest every 3 to 15
    # minutes, distant and at -6 to -9. Sharp sounds (the scold, the tick) only far and rare.
    r = s.rng
    return [
        # Day's hero: a quail's three-note call, said twice: a liquid note and two quick rising ones. Whistles,
        # so soft-edged.
        cue("quail", space(seq(*[seq(phrase(r("quail-%d" % i), shape=[(2500, 3300, 0.08), (2900, 2500, 0.05),
                                                                        (2600, 3500, 0.09)], gap=(0.11, 0.15)),
                                     silence(0.55)) for i in range(2)]), r("quail-space"), 0.8, 0.22),
            beds=["day"], every=[90, 240], level=-2, spread=0.9),

        # A bee passing some way off: a buzz that rises and falls, its pitch dropping a little.
        cue("bee", distant(tone(2.4, [(0.0, 245), (0.5, 236), (1.0, 218)],
                                ((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.35), (5, 0.25), (6, 0.15)),
                                attack=1.0, release=1.1, curve=1.5, vibrato=(7, 0.015), tremolo=(11, 0.25)), 0.4),
            beds=["day"], every=[180, 480], level=-6, spread=1.0),

        # A wren scolding a long way off: a rattling "chchchch". Sharp, so far and rare.
        cue("wren-scold", distant(space(scold(r("scold"), 12), r("scold-space"), 0.6, 0.25), 0.7),
            beds=["day"], every=[240, 600], level=-8, spread=0.9),

        # Something small moving in the brush, not near: a cluster of soft rustles; by day and by night.
        cue("rustle", distant(space(rustle(r("rustle")), r("rustle-space"), 0.5, 0.2), 0.5),
            beds=["day", "night"], every=[240, 600], level=-7, spread=0.8),

        # Night's hero: a nightjar-like call, a three-note whistle, the last note rising, said three times.
        cue("nightjar", distant(space(seq(*[seq(phrase(r("nightjar-%d" % i), shape=[(1900, 1750, 0.06),
                                                                                  (1400, 1250, 0.12),
                                                                                  (1700, 2500, 0.22)],
                                                       gap=(0.04, 0.06)), silence(0.35)) for i in range(3)]),
                                      r("nightjar-space"), 0.8, 0.25), 0.35),
            beds=["night"], every=[90, 240], level=-3, spread=0.8),

        # A far yip: two short rising barks and a longer one, a long way off.
        cue("yip", space(distant(seq(yip(r("yip-a"), 0.18), silence(0.22), yip(r("yip-b"), 0.16), silence(0.3),
                                     yip(r("yip-c"), 0.45)), 0.7), r("yip-space"), 1.2, 0.35),
            beds=["night"], every=[240, 600], level=-8, spread=1.0),

        # A moth fluttering past: soft wingbeats, about 35 a second, dulled.
        cue("moth", distant(flutter(r("moth")), 0.3),
            beds=["night"], every=[180, 600], level=-7, spread=1.0),

        # A pebble settling far off: three small ticks. Sharp, so far and rarest of all.
        cue("tick", distant(space(seq(knock(r("tick-a"), 2600, 0.06, q=12, body=0.2), silence(0.12),
                                      gain(knock(r("tick-b"), 2900, 0.05, q=12, body=0.2), -5), silence(0.08),
                                      gain(knock(r("tick-c"), 2750, 0.04, q=12, body=0.2), -10)),
                                  r("tick-space"), 0.5, 0.3), 0.7),
            beds=["night"], every=[300, 900], level=-9, spread=0.7),
    ]


def rustle(r):
    out = silence(0.9)
    for _ in range(14):
        overlay(out, noise_burst(r, r.uniform(0.02, 0.08), lo=800, hi=r.uniform(3000, 4500), attack=0.006,
                                 release=0.03), r.uniform(0.0, 0.8), r.uniform(0.3, 1.0))
    return trim(out)


def scold(r, count):
    """A scold's rattle: rapid notes, each a buzzy tone over a harsh noise."""
    rate = r.uniform(20, 24)
    out = silence(count / rate + 0.05)
    for i in range(count):
        note = add(chirp(0.02, 4800, 4300, ((1, 1.0), (2, 0.3), (3, 0.15))),
                   gain(noise_burst(r, 0.02, lo=3000, hi=7000, attack=0.002, release=0.01), -6))
        overlay(out, note, i / rate, r.uniform(0.75, 1.0))
    return trim(out)


def yip(r, seconds):
    return tone(seconds, [(0.0, 700), (0.4, 1150), (1.0, 820)], ((1, 1.0), (2, 0.5), (3, 0.3), (4, 0.15)),
                attack=0.02, release=0.06, vibrato=(r.uniform(6, 9), 0.02), breath=0.08, rng=r)


def flutter(r):
    x = noise_burst(r, 0.8, lo=150, hi=1500, attack=0.15, release=0.3)
    w = 2 * math.pi * r.uniform(32, 40) / RATE
    return [v * (0.5 + 0.5 * math.sin(w * i)) ** 2 for i, v in enumerate(x)]
