"""Snowfield: permanent snow, glaciers and the cold water at their edges.

Day is wind across a snowfield: a thin, bright rush with almost no body, a whistling edge (a few narrow
resonances that come and go on their own, as wind finds the edges of the ice), spindrift (a very fine, very high
icy hiss) and, faint and far, meltwater trickling. Night is a deeper, slower wind and the hollow tone of air
moving over ice, a few low resonances like breath over a bottle. Every distinct thing (a crack, a drip, a call)
is a cue.
"""
from lib import *

LEVEL = {"day": 0.0, "night": -2.0}


def day(s):
    # The wind, a little slower than the desert's and with fewer gusts.
    calm = drift(s.rng("wind"), s.seconds, every=6.0, lo=0.0, hi=0.6)
    g = gusts(s.rng("gusts"), s.seconds, count=6, rise=(3.0, 5.5), fall=(4.5, 8.0), size=(0.08, 0.18))
    wind = [0.45 + 0.55 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.5))]

    # The rush: thin. Pink noise with its low end taken off at 400 Hz and a cutoff that opens with the wind.
    rush = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("rush-" + side)), scale(wind, 1200, 3000)), 400, q=0.9),
                          wind) for side in "ab"], width=0.8)

    # The whistle: three narrow bands of noise (q 14) at unrelated pitches, each fading in and out on its own
    # slow drift and with the wind, so the edge of the sound keeps changing its note without ever playing a tune.
    whistles = []
    for i, hz in enumerate((1650, 2380, 3150)):
        here = drift(s.rng("whistle-%d" % i), s.seconds, every=7.0, lo=0.25, hi=1.0)
        level = [h * w for h, w in zip(here, wind)]
        whistles.append((stereo(*[apply(bandpass(pink(s.n, s.rng("whistle-%d-%s" % (i, side))), hz, q=14.0), level)
                                  for side in "ab"], width=0.7), 0))

    # The spindrift: blue noise above 6 kHz, rising more steeply than the rush in a gust, with a floor.
    drift_level = [0.35 + 0.65 * w ** 1.6 for w in smooth(wind, 2.0)]
    spindrift = stereo(*[apply(highpass(blue(s.n, s.rng("spin-" + side)), 6000), drift_level) for side in "ab"],
                       width=0.95)

    # Meltwater, far off: many tiny rising plinks too small and too many to tell apart, dulled by distance.
    plink = lambda r: chirp(r.uniform(0.006, 0.016), r.uniform(1100, 2400), r.uniform(2600, 3600))
    water = scatter(s.n, s.rng("melt"), 3500, plink, level=(-14, 0), pan=(-0.7, 0.7))
    water = (lowpass(water[0], 3500), lowpass(water[1], 3500))

    return mix((rush, 0), *[(w, -6) for w, _ in whistles], (spindrift, -6), (water, -15))


def night(s):
    # A deeper, slower wind: dark air with a new level about every 8 s.
    calm = drift(s.rng("calm"), s.seconds, every=8.0, lo=0.5, hi=0.9)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=70), scale(calm, 90, 240)), calm)
                   for side in "ab"], width=0.6)

    # The hollow tone: air over ice, as breath over a bottle. Three low resonances (q 7) on dark noise, each
    # swelling on its own, so the chord never quite settles.
    hollows = []
    for i, hz in enumerate((265, 390, 570)):
        here = drift(s.rng("hollow-%d" % i), s.seconds, every=9.0, lo=0.35, hi=1.0)
        level = [h * c for h, c in zip(here, calm)]
        hollows.append(stereo(*[apply(bandpass(pink(s.n, s.rng("hollow-%d-%s" % (i, side))), hz, q=7.0), level)
                                for side in "ab"], width=0.6))

    # Far above, a trace of spindrift so the night is not only dark.
    hiss = stereo(*[apply(highpass(blue(s.n, s.rng("hiss-" + side)), 5000), calm) for side in "ab"], width=0.9)

    return mix((air, -9), (hollows[0], 0), (hollows[1], -2), (hollows[2], -4), (hiss, -24))


def crack(r, hz):
    """Ice cracking: a sharp splintered click and a short, glassy ring."""
    out = snap(r, 0.3)
    ring = bell(hz, 0.9, partials=((1.0, 1.0, 0.18), (2.43, 0.6, 0.1), (3.91, 0.35, 0.06), (5.6, 0.2, 0.04)))
    return overlay(out, ring, 0.002, 0.35)


def echoed(r, x):
    """x and two softer, duller copies after it, as a sound comes back off a far ice wall."""
    out = list(x)
    overlay(out, distant(x, 0.45), 0.42, 0.45)
    overlay(out, distant(x, 0.75), 0.95, 0.25)
    return out


def tinkle(r):
    """Ice crystals tinkling: a dozen tiny high chimes scattered over a second and a half."""
    out = silence(1.8)
    for _ in range(r.randint(10, 14)):
        hz = r.uniform(3200, 6800)
        overlay(out, bell(hz, 0.3, partials=((1.0, 1.0, 0.06), (2.7, 0.4, 0.03))), r.uniform(0.0, 1.4),
                r.uniform(0.2, 1.0))
    return out


def cues(s):
    r = s.rng
    return [
        # Ice cracking nearby.
        cue("crack", space(crack(r("crack"), 1800), r("crack-space"), 0.9, 0.25),
            beds=["day"], every=[30, 90], level=-3, spread=0.8),

        # Snow settling: a soft, low "whumpf", by day and by night.
        cue("whumpf", seq(silence(0.02), add(noise_burst(r("whumpf"), 0.6, lo=60, hi=500, attack=0.02, release=0.45,
                                                         curve=2.0),
                                             gain(tone(0.6, (75, 45), attack=0.01, release=0.45, curve=2.0), -8))),
            beds=["day", "night"], every=[50, 140], level=-4, spread=0.7),

        # A drip falling into meltwater: a bright rising plink and a small hollow tail.
        cue("drip", space(seq(tone(0.07, (900, 2300), ((1, 1.0), (2, 0.1)), attack=0.002, release=0.04),
                              silence(0.5), gain(tone(0.06, (1000, 2500), attack=0.002, release=0.035), -7)),
                          r("drip-space"), 0.6, 0.3, 6000),
            beds=["day"], every=[15, 45], level=-4, spread=0.8),

        # A far bird: two thin, falling cries.
        cue("bird", space(distant(seq(tone(0.32, [(0.0, 1500), (0.3, 1950), (1.0, 1150)], ((1, 1.0), (2, 0.2)),
                                           attack=0.02, release=0.1, breath=0.03, rng=r("bird-a")),
                                      silence(0.35),
                                      tone(0.36, [(0.0, 1450), (0.3, 1900), (1.0, 1100)], ((1, 1.0), (2, 0.2)),
                                           attack=0.02, release=0.12, breath=0.03, rng=r("bird-b"))), 0.6),
                          r("bird-space"), 1.2, 0.3),
            beds=["day"], every=[45, 120], level=-6, spread=1.0),

        # Ice creaking under its own weight: a slow, low creak; by day and by night.
        cue("creak", space(creak(r("creak"), 1.6, rate=(14, 38), hz=(240, 600), q=8.0), r("creak-space"), 0.7, 0.2),
            beds=["day", "night"], every=[35, 100], level=-4, spread=0.8),

        # A long groan of a glacier: a low, rough tone wandering in pitch, far down in the ice.
        cue("groan", space(distant(tone(3.0, [(0.0, 92), (0.35, 120), (0.7, 104), (1.0, 80)],
                                        ((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.3), (5, 0.18), (7, 0.08)),
                                        attack=0.5, release=1.0, tremolo=(7.0, 0.35), breath=0.08, rng=r("groan")), 0.3),
                           r("groan-space"), 0.8, 0.3),
            beds=["night"], every=[50, 150], level=-4, spread=0.6),

        # A crack far across the ice, coming back twice off the far side.
        cue("far-crack", space(echoed(r("far-crack"), distant(crack(r("far-crack-a"), 1500), 0.4)),
                               r("far-crack-space"), 1.0, 0.3),
            beds=["night"], every=[40, 120], level=-5, spread=1.0),

        # Ice crystals tinkling as the wind moves them.
        cue("tinkle", space(tinkle(r("tinkle")), r("tinkle-space"), 0.6, 0.2, 7000),
            beds=["night"], every=[25, 70], level=-6, spread=0.9),

        # A far, low call across the snow: a soft hoot that rises and sinks.
        cue("call", space(distant(tone(2.2, [(0.0, 260), (0.35, 330), (1.0, 245)], ((1, 1.0), (2, 0.25), (3, 0.06)),
                                       attack=0.25, release=0.8, vibrato=(4.5, 0.01), breath=0.04, rng=r("call")), 0.7),
                          r("call-space"), 1.4, 0.35),
            beds=["night"], every=[60, 180], level=-7, spread=1.0),
    ]
