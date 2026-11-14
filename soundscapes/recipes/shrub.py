"""Scrub: thickets, heath and thorn: dry, tangled and sunlit.

Day is a dry wind hissing through thorn and twigs, thinner and brighter than a forest canopy (little body, most of
it above 2 kHz), a fine ticking of twig tips, and a few cicadas whose buzz swells and fades on its own. Night is
cooler and stiller, with a pulsing trill of tree crickets lower in pitch than the forest's chirping ones.
Everything you could pick out as one thing (a quail, a bee, a scold, a nightjar) is a cue.
"""
import math

from lib import *


def pulsed(x, hz, sharp=2.0):
    """x times a pulse train of about `hz` pulses a second, a whole number of pulses over x, so a bed stays a
    loop (memoryless, so it is seamless however the loop runs)."""
    cycles = max(1, round(hz * len(x) / RATE))
    w = 2 * math.pi * cycles / len(x)
    return [v * (0.5 + 0.5 * math.sin(w * i)) ** sharp for i, v in enumerate(x)]


def cicadas(s, count, level):
    """A few cicadas, each a narrow band of noise buzzing at its own pulse rate and pitch, fading in and out on its
    own slow drift (never quite silent), so together they swell and thin with no moment that stands out."""
    layers = []
    for k in range(count):
        r = s.rng("cicada-%d" % k)
        hz = r.uniform(4600, 6600)
        buzz = pulsed(bandpass(white(s.n, r), hz, q=r.uniform(3.0, 5.0)), r.uniform(90, 160), sharp=r.uniform(1.5, 3))
        here = drift(r, s.seconds, every=r.uniform(6.5, 9.0), lo=0.3, hi=1.0)
        layers.append((pan(apply(buzz, here), r.uniform(-0.8, 0.8)), r.uniform(-4, 0)))
    left, right = mix(*layers)
    return gain(left, level), gain(right, level)


def day(s):
    # A drier, quicker wind than the forest's: a new level about every 4 s and small gusts, kept shallow (the
    # check's `stand` fires on deep swells) and with a floor.
    calm = drift(s.rng("wind"), s.seconds, every=4.0, lo=0.0, hi=0.6)
    g = gusts(s.rng("gusts"), s.seconds, count=10, rise=(1.8, 3.5), fall=(3.0, 6.0), size=(0.06, 0.15))
    wind = [0.5 + 0.5 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.2))]

    # A thin body: there is no canopy to make the low roar, just air low over the ground.
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("body-" + side), corner=120), scale(wind, 180, 420)), wind)
                    for side in "ab"], width=0.6)

    # The hiss: pink noise above 1.8 kHz, opening upwards as the wind rises, the sound of air through thorn.
    hiss = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("hiss-" + side)), scale(wind, 4500, 9500)), 1800),
                          [w ** 1.2 for w in wind]) for side in "ab"], width=0.85)

    # Twig tips and dry leaves: many very short bright ticks, shorter and finer than the forest's leaves, never
    # stopping (a floor on what they follow).
    tick = lambda r: noise_burst(r, r.uniform(0.002, 0.008), lo=3500, hi=r.uniform(9000, 14000), attack=0.0005,
                                 release=0.004)
    twigs = scatter(s.n, s.rng("twigs"), 6000, tick, level=(-14, 0), pan=(-1, 1),
                    follow=[0.4 + 0.6 * w for w in smooth(wind, 2.0)], depth=1.0)

    return mix((body, -9), (hiss, 0), (twigs, -7), (cicadas(s, 4, 0.0), -8))


def night(s):
    # Cool still air: a low body that barely moves, and a faint high breath through the brush.
    calm = drift(s.rng("calm"), s.seconds, every=6.5, lo=0.6, hi=0.85)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=70), scale(calm, 130, 240)), calm)
                   for side in "ab"], width=0.6)
    breath = stereo(*[apply(band(pink(s.n, s.rng("breath-" + side)), 1200, 3500), calm) for side in "ab"], width=0.8)

    # Tree crickets: each caller a trill of half a second to a second, pulsing 35 to 55 times a second at about
    # 2.6 to 3.4 kHz (lower and longer than the forest's three-pulse chirps). Many overlap, so the field pulses.
    def cricket(r):
        hz, rate = r.uniform(2600, 3400), r.uniform(35, 55)
        count = int(r.uniform(0.5, 1.0) * rate)
        call = trill(r, count=count, hz=hz, each=0.55 / rate, gap=0.45 / rate)
        call = distant(call, r.uniform(0.15, 0.7))
        return lambda r2: gain(call, r2.uniform(-2, 0))
    crickets = chorus(s.n, s.rng("crickets"), voices=24, voice=cricket, rate=(0.45, 0.9), jitter=0.1,
                      level=(-8, 0), pan=(-0.9, 0.9), presence=(0.2, 1.0), every=6.0)

    return mix((air, 0), (breath, -15), (crickets, -4))


def cues(s):
    r = s.rng
    return [
        # A quail's three-note call, said twice: a sharp liquid note and two quick rising ones.
        cue("quail", space(seq(*[seq(phrase(r("quail-%d" % i), shape=[(2500, 3300, 0.08), (2900, 2500, 0.05),
                                                                        (2600, 3500, 0.09)], gap=(0.11, 0.15)),
                                     silence(0.55)) for i in range(2)]), r("quail-space"), 0.6, 0.2),
            beds=["day"], every=[25, 70], level=-2, spread=0.9),

        # Something small moving in the brush: a cluster of dry scratchy rustles over most of a second.
        cue("rustle", space(rustle(r("rustle")), r("rustle-space"), 0.4, 0.12),
            beds=["day", "night"], every=[30, 80], level=-3, spread=0.8),

        # A bee passing close: a buzz that rises and falls as it goes by, its pitch dropping a little.
        cue("bee", tone(2.4, [(0.0, 245), (0.5, 236), (1.0, 218)],
                        ((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.35), (5, 0.25), (6, 0.15), (8, 0.08)),
                        attack=1.0, release=1.1, curve=1.5, vibrato=(7, 0.015), tremolo=(11, 0.25)),
            beds=["day"], every=[30, 90], level=-4, spread=1.0),

        # A dry seed pod rattling: a quick run of tiny hard knocks, slowing and fading.
        cue("seedpod", space(roll(r("seedpod"), count=18, rate=30, hz=3200, accel=-0.4, fade=0.6,
                                  seconds_each=0.025), r("seedpod-space"), 0.4, 0.12),
            beds=["day"], every=[40, 100], level=-3, spread=0.7),

        # A wren's scold: a harsh rattling "chchchch", twice.
        cue("wren-scold", space(seq(scold(r("scold-a"), 14), silence(0.35), scold(r("scold-b"), 10)),
                                r("scold-space"), 0.5, 0.15),
            beds=["day"], every=[25, 75], level=-2, spread=0.9),

        # A nightjar-like call, far off: a three-note whistle, the last note rising, said three times.
        cue("nightjar", distant(space(seq(*[seq(phrase(r("nightjar-%d" % i), shape=[(1900, 1750, 0.06),
                                                                                  (1400, 1250, 0.12),
                                                                                  (1700, 2500, 0.22)],
                                                       gap=(0.04, 0.06)), silence(0.35)) for i in range(3)]),
                                      r("nightjar-space"), 0.8, 0.25), 0.3),
            beds=["night"], every=[30, 90], level=-3, spread=0.8),

        # A far yip: two short rising barks and a longer one, a small dog of the wild a long way off.
        cue("yip", space(distant(seq(yip(r("yip-a"), 0.18), silence(0.22), yip(r("yip-b"), 0.16), silence(0.3),
                                     yip(r("yip-c"), 0.45)), 0.65), r("yip-space"), 1.2, 0.35),
            beds=["night"], every=[45, 120], level=-7, spread=1.0),

        # A pebble or twig tick: three small hard ticks, settling.
        cue("tick", seq(knock(r("tick-a"), 2600, 0.06, q=12, body=0.2), silence(0.12),
                        gain(knock(r("tick-b"), 2900, 0.05, q=12, body=0.2), -5), silence(0.08),
                        gain(knock(r("tick-c"), 2750, 0.04, q=12, body=0.2), -10)),
            beds=["night"], every=[35, 100], level=-5, spread=0.7),

        # A moth fluttering close past: soft wingbeats, about 35 a second.
        cue("moth", flutter(r("moth")),
            beds=["night"], every=[40, 110], level=-6, spread=1.0),
    ]


def rustle(r):
    out = silence(0.9)
    for _ in range(14):
        overlay(out, noise_burst(r, r.uniform(0.02, 0.08), lo=1500, hi=r.uniform(6000, 9000), attack=0.003,
                                 release=0.03), r.uniform(0.0, 0.8), r.uniform(0.3, 1.0))
    return trim(out)


def scold(r, count):
    """A scold's rattle: rapid notes each a buzzy tone over a harsh noise."""
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
    return pulsed_one_shot(x, r.uniform(32, 40))


def pulsed_one_shot(x, hz):
    w = 2 * math.pi * hz / RATE
    return [v * (0.5 + 0.5 * math.sin(w * i)) ** 2 for i, v in enumerate(x)]
