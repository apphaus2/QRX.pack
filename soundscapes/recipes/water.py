"""Open Water: lakes, rivers, reservoirs and the sea.

Day is a calm shore: small waves lapping on shingle, the fizz of the stones as each runs back, a low wash of the
water further out and a light breeze over open water, airy and bright. Night is the same water stiller: slower,
softer, darker lapping close by, no breeze and almost no fizz. Every splash, call or bell is a cue.

The trap here is the wave. A wave that breaks at the same moment of every loop is an event, heard every 30 s, so
the lapping is hundreds of small overlapping laps at random times, none much louder than the rest, and their
density wanders with the water's own slow drift rather than coming in sets.
"""
from lib import *


def lap(r, length=(0.12, 0.32), lo=(160, 300), hi=(900, 2000)):
    """One small lap: a soft rounded puff of low-middle noise, rising slowly and falling away."""
    t = r.uniform(*length)
    return noise_burst(r, t, lo=r.uniform(*lo), hi=r.uniform(*hi), attack=t * r.uniform(0.25, 0.45),
                       release=t * r.uniform(0.45, 0.7), curve=1.6)


def fizz(r, hi=(5000, 9000)):
    """A pebble's tick or a bubble bursting as the water runs back over the shingle: a few ms of bright noise."""
    return noise_burst(r, r.uniform(0.003, 0.012), lo=2200, hi=r.uniform(*hi), attack=0.001, release=0.006)


def day(s):
    # How busy the water is: a slow wandering, new about every 6 s, kept shallow (the laps and the fizz both
    # follow it, and a lull that comes round every loop is a landmark too).
    water = drift(s.rng("water"), s.seconds, every=6.0, lo=0.55, hi=1.0)

    # Further out: a low wash, two unrelated brown noises as middle and sides.
    wash = stereo(*[apply(lowpass(brown(s.n, s.rng("wash-" + side), corner=80), 320), water) for side in "ab"],
                  width=0.6)

    # The laps: about thirty a second, overlapping, each at its own place along the shore and none much louder
    # than the rest (fewer, louder laps made single ones stand out in the 250-2k band). Under them a thin
    # continuous swash in the same band, so between laps the band is never empty.
    laps = scatter(s.n, s.rng("laps"), 900, lap, level=(-5, 0), pan=(-0.9, 0.9), follow=water, depth=0.5)
    swash = stereo(*[apply(band(pink(s.n, s.rng("swash-" + side)), 250, 1200), water) for side in "ab"], width=0.7)

    # The shingle: thousands of tiny ticks, following the laps' drift, softened so they never stop.
    shingle = scatter(s.n, s.rng("shingle"), 7000, fizz, level=(-14, 0), pan=(-1, 1),
                      follow=[0.4 + 0.6 * w for w in smooth(water, 1.0)], depth=1.0)

    # The breeze over open water: bright, wide and thin, on a wandering of its own (about 3 dB).
    air = drift(s.rng("air"), s.seconds, every=5.0, lo=0.0, hi=1.0)
    breeze = stereo(*[apply(moving_lowpass(highpass(pink(s.n, s.rng("breeze-" + side)), 1500), scale(air, 5000, 9000)),
                            [0.7 + 0.3 * a for a in air]) for side in "ab"], width=0.9)

    return mix((wash, -4), (swash, -8), (laps, 0), (shingle, -8), (breeze, -5))


def night(s):
    # Stiller: the drift slower and narrower.
    water = drift(s.rng("water"), s.seconds, every=8.0, lo=0.75, hi=1.0)

    # The body is darker and closer (narrower).
    wash = stereo(*[apply(lowpass(brown(s.n, s.rng("wash-" + side), corner=60), 220), water) for side in "ab"],
                  width=0.45)

    # Fewer, longer and darker laps, about thirty a second, just by the feet, over a dark continuous swash.
    slow = lambda r: lap(r, length=(0.25, 0.6), lo=(120, 200), hi=(500, 950))
    laps = scatter(s.n, s.rng("laps"), 900, slow, level=(-3, 0), pan=(-0.7, 0.7), follow=water, depth=0.3)
    swash = stereo(*[apply(band(pink(s.n, s.rng("swash-" + side)), 180, 800), water) for side in "ab"], width=0.5)

    # A little fizz still, much softer and duller.
    shingle = scatter(s.n, s.rng("shingle"), 2500, lambda r: fizz(r, hi=(3500, 5500)), level=(-14, 0),
                      pan=(-0.8, 0.8), follow=[0.5 + 0.5 * w for w in smooth(water, 1.5)], depth=1.0)

    # Still night air: a faint dark hush, no breeze.
    hush_level = drift(s.rng("hush"), s.seconds, every=7.0, lo=0.7, hi=1.0)
    hush = stereo(*[apply(band(pink(s.n, s.rng("hush-" + side)), 300, 1400), hush_level) for side in "ab"],
                  width=0.8)

    return mix((wash, -2), (swash, -5), (laps, 0), (shingle, -13), (hush, -16))


def splash(r, seconds=0.35, lo=250, hi=5000):
    """Water broken: a burst of noise, the body of it low, then a few drops falling back."""
    out = noise_burst(r, seconds, lo=lo, hi=hi, attack=0.004, release=seconds * 0.8, curve=2.2)
    out = overlay(out, noise_burst(r, seconds * 0.6, lo=lo * 0.5, hi=900, attack=0.01, release=seconds * 0.5), 0, 0.8)
    t = seconds * 0.7
    for _ in range(r.randint(4, 7)):
        t += r.uniform(0.04, 0.16)
        f = r.uniform(900, 2400)
        out = overlay(out, chirp(r.uniform(0.012, 0.025), f, f * 1.5), t, r.uniform(0.15, 0.4))
    return out


def plop(r, hz=(900, 300), seconds=0.09):
    """Something small dropping into still water: a falling bubble tone over a little thud of noise."""
    out = tone(seconds, hz, ((1, 1.0), (2, 0.1)), attack=0.002, release=seconds * 0.7, curve=2.0)
    return overlay(out, noise_burst(r, 0.03, lo=200, hi=2500, attack=0.001, release=0.025), 0, 0.5)


def gurgle(r):
    """Water under a jetty: a run of low bubbles, close together, a hollow knock of the boards' space under them."""
    out = silence(0.05)
    t = 0.0
    for _ in range(r.randint(9, 13)):
        t += r.uniform(0.03, 0.12)
        f = r.uniform(260, 620)
        out = overlay(out, tone(r.uniform(0.03, 0.07), (f, f * r.uniform(1.3, 1.8)), ((1, 1.0), (2, 0.15)),
                                attack=0.003, release=0.02), t, r.uniform(0.4, 1.0))
    out = overlay(out, noise_burst(r, t + 0.1, lo=150, hi=700, attack=0.05, release=0.08), 0, 0.3)
    return out


def quack(r, hz):
    """One quack: a short nasal call, falling a little."""
    t = r.uniform(0.13, 0.18)
    return tone(t, (hz * 1.05, hz * 0.85), ((1, 1.0), (2, 0.9), (3, 0.8), (4, 0.6), (5, 0.45), (6, 0.3), (8, 0.15)),
                attack=0.01, release=0.05, tremolo=(r.uniform(28, 34), 0.35))


def cues(s):
    r = s.rng
    return [
        # A fish jumps and falls back: a splash and its drops, a little way out.
        cue("fish-jump", space(distant(splash(r("fish")), 0.25), r("fish-space"), 0.5, 0.15),
            beds=["day"], every=[40, 110], level=-3, spread=0.8),

        # A gull far off over the water: three falling cries.
        cue("gull", space(distant(seq(*[seq(tone(r("gull").uniform(0.32, 0.42), [(0, 1250), (0.25, 1500), (1, 950)],
                                                 ((1, 1.0), (2, 0.5), (3, 0.25)), attack=0.03, release=0.12),
                                            silence(r("gull-gap").uniform(0.12, 0.25))) for _ in range(3)]), 0.6),
                          r("gull-space"), 1.1, 0.3),
            beds=["day"], every=[30, 90], level=-6, spread=1.0),

        # A duck on the water: a few quacks, uneven.
        cue("duck", space(seq(*[seq(quack(r("duck"), r("duck-hz").uniform(380, 440)),
                                    silence(r("duck-gap").uniform(0.08, 0.2))) for _ in range(4)]),
                          r("duck-space"), 0.5, 0.15),
            beds=["day"], every=[35, 100], level=-3, spread=0.8),

        # An oar dips and pulls: a low swirl of water, then a couple of drops from the blade.
        cue("oar", space(seq(noise_burst(r("oar"), 0.55, lo=150, hi=1400, attack=0.12, release=0.3, curve=1.5),
                             plop(r("oar-drop"), (1300, 700), 0.04), silence(0.12), plop(r("oar-drop2"), (1500, 800), 0.03)),
                         r("oar-space"), 0.4, 0.12),
            beds=["day"], every=[45, 120], level=-4, spread=0.7),

        # A far boat's bell, struck twice, softly.
        cue("boat-bell", distant(seq(bell(740, 1.4), bell(740, 2.4)), 0.55),
            beds=["day"], every=[60, 150], level=-7, spread=0.9),

        # Something small drops in near the shore; by day and by night.
        cue("plop", space(plop(r("plop")), r("plop-space"), 0.4, 0.15),
            beds=["day", "night"], every=[25, 80], level=-3, spread=0.7),

        # A loon-like call across the lake at night: a long rising, wavering wail, then a shorter one.
        cue("loon", space(distant(seq(tone(1.6, [(0, 620), (0.3, 980), (1, 900)], ((1, 1.0), (2, 0.25), (3, 0.08)),
                                           attack=0.2, release=0.4, vibrato=(5.5, 0.025)),
                                      silence(0.25),
                                      tone(1.2, [(0, 900), (0.5, 1050), (1, 760)], ((1, 1.0), (2, 0.25)),
                                           attack=0.1, release=0.45, vibrato=(6.5, 0.035))), 0.45),
                          r("loon-space"), 1.4, 0.35),
            beds=["night"], every=[45, 120], level=-4, spread=1.0),

        # A buoy's bell rocking on the swell, out in the dark: two uneven strokes, low and far.
        cue("buoy", distant(seq(bell(520, 0.9), silence(0.35), bell(520, 2.4)), 0.7),
            beds=["night"], every=[50, 130], level=-6, spread=0.9),

        # Water gurgling under a jetty, close by.
        cue("jetty", space(gurgle(r("jetty")), r("jetty-space"), 0.3, 0.2, damp=2000),
            beds=["night"], every=[30, 90], level=-4, spread=0.6),
    ]
