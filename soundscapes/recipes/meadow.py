"""Meadow: open grass, pasture and wildflowers.

Day is wind moving through long grass in broad slow waves: a soft mid-band rush with no canopy roar under it and
fewer highs than scrub, the swish of blades brushing, and far off the low hum of many insects at the flowers.
Night is nearly still air over a wide field of crickets, many and far, and a faint shimmer of those too distant
to tell apart. Everything you could pick out as one thing (a lark, a bee, a bell, a frog) is a cue.
"""
from lib import *


def day(s):
    # Broad slow waves: a knot about every 7 s and a few long, gentle gusts, so the grass leans and rises over
    # several seconds. Kept to a few dB, with a floor, so no wave is a landmark.
    calm = drift(s.rng("waves"), s.seconds, every=7.0, lo=0.0, hi=0.65)
    g = gusts(s.rng("gusts"), s.seconds, count=5, rise=(3.5, 6.0), fall=(5.0, 8.0), size=(0.08, 0.16))
    wave = [0.45 + 0.55 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 2.0))]

    # Air low over open ground: a little body, less than under trees.
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("body-" + side), corner=80), scale(wave, 150, 320)), wave)
                    for side in "ab"], width=0.6)

    # The grass: pink noise from 300 Hz, its top opening from about 1.3 to 3.5 kHz as a wave passes. Very wide,
    # since a field of grass is all around.
    grass = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("grass-" + side)), scale(wave, 1300, 3500)), 300),
                           [w ** 1.3 for w in wave]) for side in "ab"], width=0.9)

    # Blades brushing: longer, softer grains than leaves or twigs, in the middle band, following the waves late
    # and never stopping.
    blade = lambda r: noise_burst(r, r.uniform(0.03, 0.12), lo=800, hi=r.uniform(3000, 5000), attack=0.012,
                                  release=0.04)
    blades = scatter(s.n, s.rng("blades"), 3500, blade, level=(-10, 0), pan=(-1, 1),
                     follow=[0.35 + 0.65 * w for w in smooth(wave, 3.0)], depth=1.0)

    # The insect hum: a few narrow bands of noise around 170 to 280 Hz, each with a second harmonic, each
    # drifting on its own: many bees and flies at the flowers, too far to hear one.
    hums = []
    for k in range(5):
        r = s.rng("hum-%d" % k)
        hz = r.uniform(170, 280)
        here = drift(r, s.seconds, every=r.uniform(6, 9), lo=0.4, hi=1.0)
        x = add(bandpass(white(s.n, r), hz, q=6), gain(bandpass(white(s.n, r), hz * 2, q=6), -6))
        hums.append((pan(apply(x, here), r.uniform(-0.7, 0.7)), r.uniform(-4, 0)))

    return mix((body, -6), (grass, 0), (blades, -8), (mix(*hums), -16))


def night(s):
    # Air nearly still: a quiet low body that hardly moves.
    calm = drift(s.rng("calm"), s.seconds, every=8.0, lo=0.7, hi=0.85)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=60), scale(calm, 110, 200)), calm)
                   for side in "ab"], width=0.6)

    # Field crickets, many and spread wide: each a two-pulse "cri-cri" a little lower (3.5 to 4.3 kHz) and slower
    # than the forest's, most far off.
    def cricket(r):
        hz = r.uniform(3500, 4300)
        length, gap = r.uniform(0.016, 0.022), r.uniform(0.020, 0.030)
        call = seq(chirp(length, hz * 1.01, hz * 0.99), silence(gap), chirp(length, hz * 1.01, hz * 0.99))
        call = distant(call, r.uniform(0.3, 0.8))
        return lambda r2: gain(call, r2.uniform(-2, 0))
    crickets = chorus(s.n, s.rng("crickets"), voices=56, voice=cricket, rate=(0.8, 1.7), jitter=0.08,
                      level=(-7, 0), pan=(-1.0, 1.0), presence=(0.35, 1.0), every=6.0)

    # The field beyond: those too far to tell apart, a wide soft shimmer around 3 to 4.5 kHz.
    shimmer_level = drift(s.rng("shimmer"), s.seconds, every=8.0, lo=0.6, hi=1.0)
    shimmer = stereo(*[apply(band(white(s.n, s.rng("shimmer-" + side)), 3000, 4500), shimmer_level)
                       for side in "ab"], width=1.0)

    return mix((air, -6), (crickets, -3), (shimmer, -10))


def cues(s):
    r = s.rng
    return [
        # A lark overhead: a long, fast, high warble with a trill in it, a little dulled by the height.
        cue("lark", space(distant(seq(phrase(r("lark-a"), notes=12, hz=(3200, 6200), note=(0.03, 0.07),
                                             gap=(0.01, 0.03)),
                                      silence(0.04), trill(r("lark-b"), count=14, hz=5200, each=0.022, gap=0.014,
                                                           slide=0.08),
                                      silence(0.04), phrase(r("lark-c"), notes=10, hz=(3400, 6400),
                                                            note=(0.03, 0.06), gap=(0.01, 0.03))), 0.3),
                          r("lark-space"), 0.8, 0.2),
            beds=["day"], every=[20, 60], level=-3, spread=0.8),

        # A grasshopper rasping: half a dozen buzzy strokes of a leg on a wing.
        cue("grasshopper", stridulate(r("grasshopper")),
            beds=["day"], every=[25, 70], level=-5, spread=0.8),

        # A bumblebee drifting past: lower and slower than a bee, wobbling as it goes.
        cue("bumblebee", tone(3.4, [(0.0, 150), (0.4, 158), (0.7, 146), (1.0, 138)],
                              ((1, 1.0), (2, 0.8), (3, 0.6), (4, 0.45), (5, 0.3), (6, 0.2), (8, 0.1)),
                              attack=1.4, release=1.5, curve=1.5, vibrato=(4, 0.02), tremolo=(6, 0.3)),
            beds=["day"], every=[35, 100], level=-4, spread=1.0),

        # A sheep's bell, far off across the pasture: two clanks and a softer third, unevenly.
        cue("sheep-bell", space(distant(sheep_bell(r("bell")), 0.6), r("bell-space"), 1.2, 0.3),
            beds=["day"], every=[45, 120], level=-7, spread=1.0),

        # A pipit: "tsip tsip tseep", thin and high.
        cue("pipit", space(phrase(r("pipit"), shape=[(6400, 5600, 0.05), (6400, 5600, 0.05), (6200, 5000, 0.09)],
                                  gap=(0.15, 0.22)), r("pipit-space"), 0.5, 0.15),
            beds=["day"], every=[20, 60], level=-3, spread=0.9),

        # Something moving through the grass close by: soft swishes over most of a second.
        cue("grass-rustle", space(swish(r("swish")), r("swish-space"), 0.4, 0.12),
            beds=["day", "night"], every=[35, 90], level=-4, spread=0.8),

        # An owl far across the field: five low, quick hoots, not the forest owl's long call.
        cue("owl", space(distant(seq(*[seq(hoot(330 * (1 - 0.01 * i), 0.18, 0.95, rng=r("owl-%d" % i)),
                                           silence(0.16)) for i in range(5)]), 0.6), r("owl-space"), 1.0, 0.3),
            beds=["night"], every=[30, 90], level=-5, spread=0.9),

        # Frogs at a ditch: two croaks, and a higher one answering.
        cue("frog", space(seq(croak(r("frog-a"), 190, 0.3, 42), silence(0.25), croak(r("frog-b"), 185, 0.32, 42),
                              silence(0.4), gain(croak(r("frog-c"), 260, 0.22, 55), -4)), r("frog-space"), 0.6, 0.2),
            beds=["night"], every=[30, 80], level=-4, spread=0.8),

        # A fox barking a long way off: three hoarse barks.
        cue("fox", space(distant(seq(bark(r("fox-a")), silence(0.5), bark(r("fox-b")), silence(0.6),
                                     bark(r("fox-c"))), 0.55), r("fox-space"), 1.2, 0.35),
            beds=["night"], every=[45, 120], level=-6, spread=1.0),
    ]


def stridulate(r):
    """Strokes of buzzy high noise, each a burst whose grain is a run of tiny ticks about 90 a second."""
    out = silence(1.8)
    t = 0.0
    for _ in range(r.randint(6, 8)):
        d = r.uniform(0.11, 0.16)
        x = noise_burst(r, d, lo=5000, hi=12000, attack=0.02, release=0.03)
        rate = r.uniform(80, 100)
        x = [v * (1.0 if (i * rate / RATE) % 1.0 < 0.4 else 0.15) for i, v in enumerate(x)]
        overlay(out, x, t, r.uniform(0.8, 1.0))
        t += d + r.uniform(0.07, 0.1)
    return trim(out)


def sheep_bell(r):
    hz = r.uniform(760, 820)
    partials = ((1.0, 1.0, 0.5), (2.32, 0.6, 0.3), (3.9, 0.35, 0.18), (5.6, 0.2, 0.1))
    out = silence(2.4)
    for at, g in ((0.0, 1.0), (0.55, 0.8), (1.25, 0.45)):
        overlay(out, bell(hz * r.uniform(0.99, 1.01), 1.0, partials), at + r.uniform(-0.05, 0.05), g)
    return trim(out)


def swish(r):
    out = silence(0.9)
    for _ in range(8):
        overlay(out, noise_burst(r, r.uniform(0.08, 0.2), lo=700, hi=r.uniform(3500, 5000), attack=0.03,
                                 release=0.08), r.uniform(0.0, 0.65), r.uniform(0.4, 1.0))
    return trim(out)


def bark(r):
    return tone(0.2, [(0.0, 560), (0.3, 820), (1.0, 520)], ((1, 1.0), (2, 0.8), (3, 0.6), (4, 0.4), (5, 0.25)),
                attack=0.01, release=0.08, vibrato=(r.uniform(20, 30), 0.03), breath=0.25, rng=r)
