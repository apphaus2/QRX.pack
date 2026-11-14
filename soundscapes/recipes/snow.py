"""Snowfield: permanent snow, glaciers and the cold water at their edges.

A soft backdrop, not a portrait. Day is a thin, cool wind across the snow: little low body, a soft rush, and a
faint, low whistle that wanders between nearby notes as the wind finds the edges of the ice, never held long
enough to be a tune; under it the faintest dull spindrift and, far off, meltwater trickling. Night is a deeper,
slower wind and the hollow tone of air over ice, a few low resonances like breath over a bottle. Events are cues,
rare and mostly far; each bed has one soft hero (a far bird by day, a far low call by night).
"""
from lib import *

LEVEL = {"day": 0.0, "night": -2.0}


def day(s):
    # The wind: slower and steadier than the desert's, about 4 dB from lull to swell.
    calm = drift(s.rng("wind"), s.seconds, every=7.0, lo=0.0, hi=0.45)
    g = gusts(s.rng("gusts"), s.seconds, count=5, rise=(3.0, 6.0), fall=(5.0, 8.0), size=(0.06, 0.14))
    wind = [0.6 + 0.4 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.5))]

    # The rush: thin. Pink noise with its low end taken off at 300 Hz and a cutoff that opens from 500 to 1500 Hz.
    rush = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("rush-" + side)), scale(wind, 500, 1500)), 300),
                          wind) for side in "ab"], width=0.8)

    # Only a trace of dark body, so the snow sounds hollow rather than heavy.
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("body-" + side), corner=90), scale(wind, 150, 300)), wind)
                    for side in "ab"], width=0.6)

    # The whistle, low and wandering: five narrow bands (q 9) a little apart, 640 to 1150 Hz, each fading in and
    # out on its own drift (squared, so mostly one or two sound at a time), so the note slides about.
    whistles = []
    for i, hz in enumerate((640, 750, 860, 990, 1150)):
        here = [h * h for h in drift(s.rng("whistle-%d" % i), s.seconds, every=6.0, lo=0.0, hi=1.0)]
        level = [0.15 + 0.85 * h * w for h, w in zip(here, wind)]
        whistles.append((stereo(*[apply(bandpass(pink(s.n, s.rng("whistle-%d-%s" % (i, side))), hz, q=9.0), level)
                                  for side in "ab"], width=0.7), -9))

    # Spindrift: a faint, dull grain of ice, tiny puffs from 1.2 to under 3.5 kHz, thicker in a gust.
    grain = lambda r: noise_burst(r, r.uniform(0.002, 0.006), lo=1200, hi=r.uniform(2500, 3500), attack=0.0008,
                                  release=0.003)
    spindrift = scatter(s.n, s.rng("spin"), 5000, grain, level=(-12, 0), pan=(-1, 1),
                        follow=[0.4 + 0.6 * w for w in smooth(wind, 2.0)], depth=1.0)

    # Meltwater far off: many tiny rising plinks too small and too many to tell apart, under 2 kHz by distance.
    plink = lambda r: chirp(r.uniform(0.008, 0.018), r.uniform(700, 1300), r.uniform(1400, 2000))
    water = scatter(s.n, s.rng("melt"), 3000, plink, level=(-14, 0), pan=(-0.7, 0.7))
    water = (lowpass(water[0], 1800), lowpass(water[1], 1800))

    return mix((rush, 0), (body, -9), *whistles, (spindrift, -16), (water, -18))


def night(s):
    # A deeper, slower wind: dark air with a new level about every 8 s.
    calm = drift(s.rng("calm"), s.seconds, every=8.0, lo=0.5, hi=0.9)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=70), scale(calm, 90, 240)), calm)
                   for side in "ab"], width=0.6)

    # The hollow tone: three low resonances (q 7) on pink noise, each swelling on its own, so the chord never
    # quite settles. They lift the night's middle above the desert night's, which is breath and ticks.
    hollows = []
    for i, hz in enumerate((265, 390, 570)):
        here = drift(s.rng("hollow-%d" % i), s.seconds, every=9.0, lo=0.35, hi=1.0)
        level = [h * c for h, c in zip(here, calm)]
        hollows.append(stereo(*[apply(bandpass(pink(s.n, s.rng("hollow-%d-%s" % (i, side))), hz, q=7.0), level)
                                for side in "ab"], width=0.6))

    return mix((air, -9), (hollows[0], 0), (hollows[1], -2), (hollows[2], -4))


def crack(r, hz):
    """Ice cracking: a splintered click and a short, glassy ring."""
    out = snap(r, 0.3)
    ring = bell(hz, 0.9, partials=((1.0, 1.0, 0.18), (2.43, 0.6, 0.1), (3.91, 0.35, 0.06), (5.6, 0.2, 0.04)))
    return overlay(out, ring, 0.002, 0.35)


def echoed(x):
    """x and two softer, duller copies after it, as a sound comes back off a far ice wall."""
    out = list(x)
    overlay(out, distant(x, 0.45), 0.42, 0.45)
    overlay(out, distant(x, 0.75), 0.95, 0.25)
    return out


def tinkle(r):
    """Ice crystals tinkling: a dozen tiny chimes over a second and a half, soft-struck."""
    out = silence(1.8)
    for _ in range(r.randint(10, 14)):
        hz = r.uniform(2400, 4800)
        overlay(out, bell(hz, 0.3, partials=((1.0, 1.0, 0.06), (2.7, 0.4, 0.03)), attack=0.004),
                r.uniform(0.0, 1.4), r.uniform(0.2, 1.0))
    return out


def cues(s):
    # Rare and mostly far: each hero every 90 to 240 s, the rest every 3 to 15 minutes, so about one event a
    # minute or less. Only the heroes are above level -4; the cracks are sharp by nature, so far and rare.
    r = s.rng
    return [
        # Day's hero: a far bird, two thin falling cries.
        cue("bird", space(distant(seq(tone(0.34, [(0.0, 1500), (0.3, 1950), (1.0, 1150)], ((1, 1.0), (2, 0.2)),
                                           attack=0.04, release=0.12, breath=0.03, rng=r("bird-a")),
                                      silence(0.35),
                                      tone(0.38, [(0.0, 1450), (0.3, 1900), (1.0, 1100)], ((1, 1.0), (2, 0.2)),
                                           attack=0.04, release=0.14, breath=0.03, rng=r("bird-b"))), 0.45),
                          r("bird-space"), 1.2, 0.3),
            beds=["day"], every=[90, 240], level=-3, spread=1.0),

        # Snow settling: a soft, low "whumpf"; by day and by night.
        cue("whumpf", seq(silence(0.02), add(noise_burst(r("whumpf"), 0.6, lo=60, hi=450, attack=0.03, release=0.45,
                                                         curve=2.0),
                                             gain(tone(0.6, (110, 70), attack=0.02, release=0.45, curve=2.0), -8))),
            beds=["day", "night"], every=[180, 480], level=-6, spread=0.7),

        # A drip falling into meltwater some way off: a rising plink and a small hollow tail.
        cue("drip", distant(space(seq(tone(0.07, (800, 1900), ((1, 1.0), (2, 0.1)), attack=0.006, release=0.04),
                                      silence(0.5), gain(tone(0.06, (900, 2000), attack=0.006, release=0.035), -7)),
                                  r("drip-space"), 0.6, 0.3, 4000), 0.5),
            beds=["day"], every=[180, 600], level=-7, spread=0.8),

        # Ice creaking under its own weight, far down: a slow, low creak; by day and by night.
        cue("creak", distant(space(creak(r("creak"), 1.6, rate=(14, 38), hz=(240, 600), q=8.0), r("creak-space"),
                                   0.7, 0.25), 0.5),
            beds=["day", "night"], every=[240, 600], level=-7, spread=0.8),

        # Ice cracking far across the field: sharp by nature, so far, dull and rare.
        cue("crack", space(distant(crack(r("crack"), 1500), 0.8), r("crack-space"), 1.0, 0.35),
            beds=["day"], every=[300, 900], level=-9, spread=0.9),

        # Night's hero: a far, low call across the snow, a soft hoot that rises and sinks.
        cue("call", space(distant(tone(2.2, [(0.0, 260), (0.35, 330), (1.0, 245)], ((1, 1.0), (2, 0.25), (3, 0.06)),
                                       attack=0.25, release=0.8, vibrato=(4.5, 0.01), breath=0.04, rng=r("call")), 0.5),
                          r("call-space"), 1.4, 0.35),
            beds=["night"], every=[90, 240], level=-2, spread=1.0),

        # A long groan of a glacier: a low, rough tone wandering in pitch, far down in the ice.
        cue("groan", space(distant(tone(3.0, [(0.0, 92), (0.35, 120), (0.7, 104), (1.0, 80)],
                                        ((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.3), (5, 0.18), (7, 0.08)),
                                        attack=0.5, release=1.0, tremolo=(7.0, 0.35), breath=0.08, rng=r("groan")), 0.4),
                           r("groan-space"), 0.8, 0.3),
            beds=["night"], every=[240, 600], level=-6, spread=0.6),

        # A crack very far across the ice, coming back twice off the far side.
        cue("far-crack", space(echoed(distant(crack(r("far-crack"), 1300), 0.8)), r("far-crack-space"), 1.0, 0.35),
            beds=["night"], every=[300, 900], level=-9, spread=1.0),

        # Ice crystals tinkling as the air moves them, a little way off.
        cue("tinkle", distant(space(tinkle(r("tinkle")), r("tinkle-space"), 0.6, 0.25, 5000), 0.6),
            beds=["night"], every=[300, 720], level=-8, spread=0.9),
    ]
