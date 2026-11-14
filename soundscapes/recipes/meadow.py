"""Meadow: open grass, pasture and wildflowers.

A soft backdrop, not a portrait. Day is wind through long grass in broad slow waves: a soft mid-band rush with
little body under it (no trees), the blades' dull brush, and far off the low hum of many insects at the flowers,
which is what sets it apart from the forest and the scrub. Night is nearly still air with a wide field of crickets
far away, faint and spread all round. Anything you could pick out as one thing is a cue, and cues are rare (about
one a minute or less) and mostly far; the hero by day is a lark overhead, by night an owl across the field.
"""
from lib import *


def day(s):
    # Broad slow waves: a knot about every 7 s and a few long, gentle gusts, so the grass leans and rises over
    # several seconds; shallow and over a floor, so no wave is a landmark.
    calm = drift(s.rng("waves"), s.seconds, every=7.0, lo=0.0, hi=0.5)
    g = gusts(s.rng("gusts"), s.seconds, count=5, rise=(3.5, 6.0), fall=(5.0, 8.0), size=(0.06, 0.14))
    wave = [0.55 + 0.45 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 2.0))]

    # Air low over open ground: a little body.
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("body-" + side), corner=80), scale(wave, 150, 300)), wave)
                    for side in "ab"], width=0.6)

    # The grass: pink noise from 250 Hz, its top opening from about 800 Hz to 1.4 kHz as a wave passes, very wide.
    grass = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("grass-" + side)), scale(wave, 800, 1400)), 250),
                           [w ** 1.2 for w in wave]) for side in "ab"], width=0.9)

    # Blades brushing: long, soft grains from 600 Hz to about 2.4 kHz, following the waves late, never stopping.
    blade = lambda r: noise_burst(r, r.uniform(0.03, 0.12), lo=600, hi=r.uniform(1600, 2400), attack=0.015,
                                  release=0.04)
    blades = scatter(s.n, s.rng("blades"), 3500, blade, level=(-10, 0), pan=(-1, 1),
                     follow=[0.4 + 0.6 * w for w in smooth(wave, 3.0)], depth=1.0)

    # The insect hum: narrow bands of noise around 170 to 280 Hz with a second harmonic, each drifting on its own:
    # many bees and flies at the flowers, too far to hear one. Narrow noise, not sines (a looped sine stack can
    # read as a seam).
    hums = []
    for k in range(5):
        r = s.rng("hum-%d" % k)
        hz = r.uniform(170, 280)
        here = drift(r, s.seconds, every=r.uniform(6, 9), lo=0.5, hi=1.0)
        x = add(bandpass(white(s.n, r), hz, q=6), gain(bandpass(white(s.n, r), hz * 2, q=6), -6))
        hums.append((pan(apply(x, here), r.uniform(-0.7, 0.7)), r.uniform(-3, 0)))

    return mix((body, -6), (grass, 0), (blades, -9), (mix(*hums), -9))


def night(s):
    # Air nearly still: a quiet low body that hardly moves, and a faint breath of the grass.
    calm = drift(s.rng("calm"), s.seconds, every=8.0, lo=0.7, hi=0.85)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=60), scale(calm, 110, 200)), calm)
                   for side in "ab"], width=0.6)
    grass = stereo(*[apply(band(pink(s.n, s.rng("grass-" + side)), 250, 900), calm) for side in "ab"], width=0.9)

    # The field: many crickets, a two-pulse "cri-cri" at 3.2 to 3.8 kHz (lower than the forest's), all far off
    # and spread all round, so they make a faint wide presence rather than a chorus at the listener's feet.
    def cricket(r):
        hz = r.uniform(3200, 3800)
        length, gap = r.uniform(0.016, 0.022), r.uniform(0.020, 0.030)
        call = seq(chirp(length, hz * 1.01, hz * 0.99), silence(gap), chirp(length, hz * 1.01, hz * 0.99))
        call = distant(call, r.uniform(0.5, 0.9))
        return lambda r2: gain(call, r2.uniform(-2, 0))
    crickets = chorus(s.n, s.rng("crickets"), voices=56, voice=cricket, rate=(0.8, 1.7), jitter=0.08,
                      level=(-7, 0), pan=(-1.0, 1.0), presence=(0.35, 1.0), every=6.0)

    return mix((air, 0), (grass, -16), (crickets, -6))


def cues(s):
    # Rare and mostly far (README, "Cues are rare"): each bed's hero every 90 to 240 s, the rest every 3 to 10
    # minutes, distant and at -6 to -8.
    r = s.rng
    return [
        # Day's hero: a lark high overhead, a long fast warble with a trill in it, dulled by the height.
        cue("lark", space(distant(seq(phrase(r("lark-a"), notes=12, hz=(3200, 6200), note=(0.03, 0.07),
                                             gap=(0.01, 0.03)),
                                      silence(0.04), trill(r("lark-b"), count=14, hz=5200, each=0.022, gap=0.014,
                                                           slide=0.08),
                                      silence(0.04), phrase(r("lark-c"), notes=10, hz=(3400, 6400),
                                                            note=(0.03, 0.06), gap=(0.01, 0.03))), 0.35),
                          r("lark-space"), 0.8, 0.22),
            beds=["day"], every=[90, 240], level=-2, spread=0.8),

        # A grasshopper rasping a little way off: half a dozen buzzy strokes.
        cue("grasshopper", distant(stridulate(r("grasshopper")), 0.5),
            beds=["day"], every=[240, 600], level=-7, spread=0.8),

        # A bumblebee drifting past, not close: low and slow, wobbling as it goes.
        cue("bumblebee", distant(tone(3.4, [(0.0, 150), (0.4, 158), (0.7, 146), (1.0, 138)],
                                      ((1, 1.0), (2, 0.8), (3, 0.6), (4, 0.45), (5, 0.3), (6, 0.2)),
                                      attack=1.4, release=1.5, curve=1.5, vibrato=(4, 0.02), tremolo=(6, 0.3)), 0.35),
            beds=["day"], every=[180, 600], level=-6, spread=1.0),

        # A sheep's bell, far off across the pasture: two clanks and a softer third, unevenly.
        cue("sheep-bell", space(distant(sheep_bell(r("bell")), 0.7), r("bell-space"), 1.2, 0.3),
            beds=["day"], every=[240, 600], level=-8, spread=1.0),

        # Something moving through the grass some way off: soft swishes; by day and by night.
        cue("grass-rustle", distant(space(swish(r("swish")), r("swish-space"), 0.5, 0.2), 0.45),
            beds=["day", "night"], every=[240, 600], level=-7, spread=0.8),

        # Night's hero: an owl across the field, five low, quick hoots (not the forest owl's long call).
        cue("owl", space(distant(seq(*[seq(hoot(330 * (1 - 0.01 * i), 0.18, 0.95, rng=r("owl-%d" % i)),
                                           silence(0.16)) for i in range(5)]), 0.5), r("owl-space"), 1.0, 0.3),
            beds=["night"], every=[90, 240], level=-3, spread=0.9),

        # Frogs at a far ditch: two croaks, and a higher one answering.
        cue("frog", distant(space(seq(croak(r("frog-a"), 190, 0.3, 42), silence(0.25),
                                      croak(r("frog-b"), 185, 0.32, 42), silence(0.4),
                                      gain(croak(r("frog-c"), 260, 0.22, 55), -4)), r("frog-space"), 0.6, 0.25), 0.45),
            beds=["night"], every=[180, 480], level=-6, spread=0.8),

        # A fox barking a long way off: three hoarse barks.
        cue("fox", space(distant(seq(bark(r("fox-a")), silence(0.5), bark(r("fox-b")), silence(0.6),
                                     bark(r("fox-c"))), 0.7), r("fox-space"), 1.2, 0.35),
            beds=["night"], every=[240, 600], level=-8, spread=1.0),
    ]


def stridulate(r):
    """Strokes of buzzy noise, each a burst whose grain is a run of tiny ticks about 90 a second."""
    out = silence(1.8)
    t = 0.0
    for _ in range(r.randint(6, 8)):
        d = r.uniform(0.11, 0.16)
        x = noise_burst(r, d, lo=4000, hi=9000, attack=0.02, release=0.03)
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
        overlay(out, noise_burst(r, r.uniform(0.08, 0.2), lo=600, hi=r.uniform(2500, 4000), attack=0.03,
                                 release=0.08), r.uniform(0.0, 0.65), r.uniform(0.4, 1.0))
    return trim(out)


def bark(r):
    return tone(0.2, [(0.0, 560), (0.3, 820), (1.0, 520)], ((1, 1.0), (2, 0.8), (3, 0.6), (4, 0.4), (5, 0.25)),
                attack=0.01, release=0.08, vibrato=(r.uniform(20, 30), 0.03), breath=0.25, rng=r)
