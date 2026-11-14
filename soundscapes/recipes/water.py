"""Open Water: lakes, rivers, reservoirs and the sea.

A soft backdrop, not a portrait. Day is calm water by a shore: a low, dark wash of the water further out, long
gentle swells of soft lapping close by, a faint dull trace of the shingle as the water draws back, and a little
open air above. Night is the same water stiller and darker: slower, longer swells, no shingle, no air. Cues are
rare and mostly far; each bed has one hero, the sound that says "water" (a gull far over the lake by day, a loon
across it at night).

The trap here is the wave. A wave that breaks at the same moment of every loop is an event heard every 30 s, so
the lapping is many long, soft, overlapping swells of dull noise at random times, none much louder than the rest,
over a continuous swash in the same band: the second version keeps its laps long and few (about ten a second,
each one to two seconds, so several overlap) where the first had thirty short ones a second over seven thousand shingle ticks.
"""
from lib import *


def lap(r, length=(0.9, 1.8), lo=(120, 200), hi=(500, 900)):
    """One soft swell of water against the shore: a long rounded puff of low, dull noise, rising slowly and
    falling away more slowly."""
    t = r.uniform(*length)
    return noise_burst(r, t, lo=r.uniform(*lo), hi=r.uniform(*hi), attack=t * r.uniform(0.3, 0.45),
                       release=t * r.uniform(0.5, 0.65), curve=1.3)


def day(s):
    # How busy the water is: a slow wandering, a new level about every 7 s, kept shallow (about 2 dB). The
    # laps and the swash both follow it.
    water = drift(s.rng("water"), s.seconds, every=7.0, lo=0.8, hi=1.0)

    # Further out: a low wash, two unrelated brown noises as middle and sides.
    wash = stereo(*[apply(lowpass(brown(s.n, s.rng("wash-" + side), corner=80), 280), water) for side in "ab"],
                  width=0.6)

    # Close by: a continuous swash, so between swells the band is never empty, and the swells themselves,
    # long, soft and overlapping.
    swash = stereo(*[apply(band(pink(s.n, s.rng("swash-" + side)), 180, 900), water) for side in "ab"], width=0.7)
    laps = scatter(s.n, s.rng("laps"), 320, lap, level=(-2, 0), pan=(-0.8, 0.8), follow=water, depth=0.3)

    # The shingle: a faint, dull trace of small grains as the water draws back (1.2 to 3 kHz at most, never the
    # bright fizz of the first version), thicker where the water is busier, never stopping.
    tick = lambda r: noise_burst(r, r.uniform(0.006, 0.02), lo=1200, hi=r.uniform(2200, 3200), attack=0.002,
                                 release=0.012)
    shingle = scatter(s.n, s.rng("shingle"), 1500, tick, level=(-10, 0), pan=(-1, 1),
                      follow=[0.5 + 0.5 * w for w in smooth(water, 1.5)], depth=1.0)

    # A little open air over the water: dull, wide, barely there, on a wandering of its own.
    air = drift(s.rng("air"), s.seconds, every=6.0, lo=0.75, hi=1.0)
    breeze = stereo(*[apply(band(pink(s.n, s.rng("breeze-" + side)), 500, 1600), air) for side in "ab"], width=0.9)

    return mix((wash, -3), (swash, -4), (laps, -3), (shingle, -16), (breeze, -12))


def night(s):
    # Stiller: the drift slower and even shallower.
    water = drift(s.rng("water"), s.seconds, every=9.0, lo=0.78, hi=1.0)

    # The body is darker and closer (narrower).
    wash = stereo(*[apply(lowpass(brown(s.n, s.rng("wash-" + side), corner=60), 200), water) for side in "ab"],
                  width=0.45)

    # Slower, longer, darker swells over a darker swash, and nothing above them.
    swash = stereo(*[apply(band(pink(s.n, s.rng("swash-" + side)), 140, 600), water) for side in "ab"], width=0.5)
    slow = lambda r: lap(r, length=(1.4, 2.6), lo=(90, 150), hi=(350, 600))
    laps = scatter(s.n, s.rng("laps"), 100, slow, level=(-3, 0), pan=(-0.6, 0.6), follow=water, depth=0.3)

    return mix((wash, 0), (swash, -5), (laps, -3))


def splash(r, seconds=0.35, lo=200, hi=2500):
    """Water broken: a soft burst of noise, the body of it low, then a few drops falling back."""
    out = noise_burst(r, seconds, lo=lo, hi=hi, attack=0.02, release=seconds * 0.8, curve=1.8)
    out = overlay(out, noise_burst(r, seconds * 0.6, lo=lo * 0.5, hi=800, attack=0.03, release=seconds * 0.5), 0, 0.8)
    t = seconds * 0.7
    for _ in range(r.randint(3, 5)):
        t += r.uniform(0.06, 0.18)
        f = r.uniform(700, 1600)
        out = overlay(out, chirp(r.uniform(0.015, 0.03), f, f * 1.4), t, r.uniform(0.1, 0.25))
    return out


def plop(r, hz=(700, 260), seconds=0.12):
    """Something small dropping into still water: a falling bubble tone over a little soft thud."""
    out = tone(seconds, hz, ((1, 1.0), (2, 0.1)), attack=0.006, release=seconds * 0.7, curve=1.6)
    return overlay(out, noise_burst(r, 0.04, lo=150, hi=1500, attack=0.004, release=0.03), 0, 0.4)


def gurgle(r):
    """Water under a jetty: a run of low bubbles, close together, with a hollow wash under them."""
    out = silence(0.05)
    t = 0.0
    for _ in range(r.randint(8, 11)):
        t += r.uniform(0.05, 0.14)
        f = r.uniform(240, 520)
        out = overlay(out, tone(r.uniform(0.04, 0.08), (f, f * r.uniform(1.3, 1.6)), ((1, 1.0), (2, 0.12)),
                                attack=0.008, release=0.03), t, r.uniform(0.4, 1.0))
    return overlay(out, noise_burst(r, t + 0.15, lo=120, hi=600, attack=0.08, release=0.1), 0, 0.3)


def quack(r, hz):
    """One quack: a short nasal call, falling a little."""
    t = r.uniform(0.13, 0.18)
    return tone(t, (hz * 1.05, hz * 0.85), ((1, 1.0), (2, 0.9), (3, 0.8), (4, 0.6), (5, 0.45), (6, 0.3), (8, 0.15)),
                attack=0.015, release=0.05, tremolo=(r.uniform(28, 34), 0.35))


def gull(r):
    """Three falling cries, each a little different."""
    return seq(*[seq(tone(r.uniform(0.34, 0.44), [(0, 1200), (0.25, 1450), (1, 920)], ((1, 1.0), (2, 0.4), (3, 0.15)),
                          attack=0.05, release=0.14), silence(r.uniform(0.15, 0.3))) for _ in range(3)])


def cues(s):
    # Rare and mostly far: each bed's hero every 90 to 240 s, the others every 3 to 15 minutes, so about one
    # event a minute or less. Only the hero is above level -4, and it is tonal and soft-edged.
    r = s.rng
    return [
        # Day's hero: a gull over the water, some way off, in the open air.
        cue("gull", space(distant(gull(r("gull")), 0.35), r("gull-space"), 1.1, 0.3),
            beds=["day"], every=[90, 240], level=-3, spread=1.0),

        # A fish jumps and falls back, well out on the water.
        cue("fish-jump", distant(space(splash(r("fish")), r("fish-space"), 0.6, 0.25), 0.6),
            beds=["day"], every=[180, 600], level=-7, spread=0.8),

        # A duck on the far side: a few uneven quacks.
        cue("duck", distant(space(seq(*[seq(quack(r("duck-%d" % i), 380 + 15 * i), silence(0.1 + 0.04 * i))
                                        for i in range(4)]), r("duck-space"), 0.6, 0.25), 0.55),
            beds=["day"], every=[240, 600], level=-6, spread=0.9),

        # An oar dipping somewhere out on the lake: a low swirl of water and a drop from the blade.
        cue("oar", distant(space(seq(noise_burst(r("oar"), 0.6, lo=120, hi=1000, attack=0.15, release=0.35, curve=1.4),
                                     plop(r("oar-drop"), (1000, 600), 0.05)), r("oar-space"), 0.5, 0.2), 0.5),
            beds=["day"], every=[240, 600], level=-7, spread=0.8),

        # A far boat's bell, struck twice, softly.
        cue("boat-bell", distant(seq(bell(740, 1.4), bell(740, 2.4)), 0.75),
            beds=["day"], every=[300, 900], level=-8, spread=0.9),

        # Night's hero: a loon-like call across the lake, a long rising, wavering wail and a shorter one.
        cue("loon", space(distant(seq(tone(1.6, [(0, 620), (0.3, 980), (1, 900)], ((1, 1.0), (2, 0.25), (3, 0.08)),
                                           attack=0.25, release=0.45, vibrato=(5.5, 0.025)),
                                      silence(0.25),
                                      tone(1.2, [(0, 900), (0.5, 1050), (1, 760)], ((1, 1.0), (2, 0.25)),
                                           attack=0.15, release=0.45, vibrato=(6.5, 0.035))), 0.5),
                          r("loon-space"), 1.4, 0.35),
            beds=["night"], every=[90, 240], level=-2, spread=1.0),

        # A buoy's bell rocking on the swell, far out in the dark: two uneven strokes.
        cue("buoy", distant(seq(bell(520, 0.9), silence(0.35), bell(520, 2.4)), 0.8),
            beds=["night"], every=[240, 600], level=-8, spread=0.9),

        # Something small drops in, a little way along the shore.
        cue("plop", distant(space(plop(r("plop")), r("plop-space"), 0.5, 0.25), 0.5),
            beds=["night"], every=[180, 600], level=-7, spread=0.7),

        # Water gurgling under a jetty, along the shore.
        cue("jetty", distant(space(gurgle(r("jetty")), r("jetty-space"), 0.4, 0.25, damp=2000), 0.4),
            beds=["night"], every=[240, 600], level=-6, spread=0.6),
    ]
