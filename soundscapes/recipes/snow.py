"""Snowfield: permanent snow, glaciers and the cold water at their edges.

A soft backdrop, not a portrait. Day is a thin, cool wind across the snow: little low body, a soft rush, and a
faint, low whistle of several nearby notes at once whose colour shifts slowly as the wind finds the edges of the
ice; under it the faintest dull hiss of spindrift. Night is a deeper, slower wind and the hollow tone of air over
ice, a few low resonances like breath over a bottle. A bed holds only continuous texture. Events are cues,
rare and mostly far; each bed has one soft hero (a far bird by day, a far low call by night).
"""
from lib import *

LEVEL = {"day": 0.0, "night": -2.0}


def day(s):
    # The wind: a slow, shallow wandering, a new level about every 11 s, about 2 dB deep, and no gusts (the owner,
    # 2026-11-17: the beds were too active).
    wind = scale(drift(s.rng("wind"), s.seconds, every=11.0), 0.78, 1.0)

    # The rush: thin. Pink noise with its low end taken off at 300 Hz and a cutoff that moves from 800 to 1300 Hz.
    rush = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("rush-" + side)), scale(wind, 800, 1300)), 300),
                          wind) for side in "ab"], width=0.8)

    # Only a trace of dark body, so the snow sounds hollow rather than heavy.
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("body-" + side), corner=90), scale(wind, 170, 260)), wind)
                    for side in "ab"], width=0.6)

    # The whistle, low and soft: five narrow bands (q 9) a little apart, 640 to 1150 Hz, all sounding at once, each
    # rising and settling a little on its own slow drift, so the tone of the wind shifts without a note ever coming
    # forward (the second version squared the drifts, so one or two notes at a time stood out and slid about).
    whistles = []
    for i, hz in enumerate((640, 750, 860, 990, 1150)):
        here = drift(s.rng("whistle-%d" % i), s.seconds, every=12.0, lo=0.6, hi=1.0)
        level = [h * w for h, w in zip(here, wind)]
        whistles.append((stereo(*[apply(bandpass(pink(s.n, s.rng("whistle-%d-%s" % (i, side))), hz, q=9.0), level)
                                  for side in "ab"], width=0.7), -14))

    # Spindrift, too fine to hear a grain: a faint, dull, continuous hiss of ice from 1.2 to 3.2 kHz on its own
    # slow wandering. The second version's spindrift puffs and far meltwater plinks are gone: each was a tick.
    spin_level = scale(drift(s.rng("spin"), s.seconds, every=12.0), 0.8, 1.0)
    spindrift = stereo(*[apply(band(pink(s.n, s.rng("spin-" + side)), 1200, 3200), spin_level) for side in "ab"],
                       width=0.9)

    return mix((rush, 0), (body, -9), *whistles, (spindrift, -18))


def night(s):
    # A deeper, slower wind: dark air with a new level about every 12 s.
    calm = scale(drift(s.rng("calm"), s.seconds, every=12.0), 0.85, 1.0)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=70), scale(calm, 120, 200)), calm)
                   for side in "ab"], width=0.6)

    # The hollow tone: three low resonances (q 7) on pink noise, each rising and settling slowly on its own, so
    # the chord never quite settles. They lift the night's middle above the desert night's, which is breath.
    hollows = []
    for i, hz in enumerate((265, 390, 570)):
        here = drift(s.rng("hollow-%d" % i), s.seconds, every=13.0, lo=0.7, hi=1.0)
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
