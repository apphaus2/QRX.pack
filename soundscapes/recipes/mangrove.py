"""Mangrove: tidal forest, roots, mud and brackish water.

Day is warm, close and wet: tide water moving among the roots (a soft slosh with a gurgle in it), the mud
popping and ticking as it drains, and a dense whine of tropical insects hanging over everything in the still
air. Night keeps the tide, slower, thickens the insects into a pulsing chorus, and adds the fine crackle of
snapping shrimp under the water. Crabs, birds, drips, frogs and bats are cues.

The sounds that set it apart from the forest: water and mud in the middle band by day (the forest's middle band
is wind in the crowns), and a steady high whine and shrimp crackle where the forest has leaves or crickets.
"""
import math

from lib import *


def whine(n, rng, freqs, q=40.0):
    """An insect whine: white noise through narrow resonances at `freqs`, so each is a tone that wavers in pitch
    and level by itself. (Steady sine tones were tried first: they loop exactly, but a few beating partials at
    3-7 kHz have a crest that made the check's `seam` measure read over 1.0 under some seeds.)"""
    return set_rms(add(*[bandpass(white(n, rng), f, q) for f in freqs]))


def bubble(r, lo=300, hi=1100, seconds=(0.015, 0.05)):
    """A small rising blip of water: a gurgle among roots, a pop in the mud."""
    d = r.uniform(*seconds)
    f = r.uniform(lo, hi)
    return tone(d, (f, f * r.uniform(1.4, 2.0)), ((1, 1.0), (2, 0.1)), attack=0.002, release=d * 0.8, curve=2.0)


def tick(r):
    """The mud ticking as it drains: a tiny dry click."""
    return knock(r, r.uniform(1800, 4200), 0.018, q=3.0, body=0.0)


def tide(s, name, every, lo, hi, cutoff):
    """The water among the roots: pink noise in the low middle band, its brightness and level wandering slowly,
    and a gurgle of many small bubbles that is busier where the water is moving more. Both are dense and have a
    floor, so a stretch of quiet water never empties into a landmark."""
    flow = drift(s.rng(name), s.seconds, every=every, lo=lo, hi=hi)
    slosh = stereo(*[apply(band(moving_lowpass(pink(s.n, s.rng(name + "-" + side)), scale(flow, *cutoff)), 180, 2400),
                           flow) for side in "ab"], width=0.75)
    gurgle = scatter(s.n, s.rng(name + "-gurgle"), 5000, bubble, level=(-16, -2), pan=(-0.9, 0.9),
                     follow=[0.4 + 0.6 * v for v in smooth(flow, 1.5)], depth=0.7)
    return slosh, gurgle


def day(s):
    # Humid stillness: a dark, barely moving body of air so the bed has a floor under the water.
    still = drift(s.rng("still"), s.seconds, every=7.0, lo=0.75, hi=0.95)
    air = stereo(*[apply(lowpass(brown(s.n, s.rng("air-" + side), corner=80), 220), still) for side in "ab"],
                 width=0.6)

    slosh, gurgle = tide(s, "tide", 5.0, 0.6, 1.0, (500, 1300))

    # The mud: thousands of tiny ticks and soft pops, never in a cluster big enough to hear as one event.
    mud = scatter(s.n, s.rng("mud"), 6000, tick, level=(-20, -6), pan=(-1, 1))
    pops = scatter(s.n, s.rng("pops"), 2500, lambda r: bubble(r, 500, 1600, (0.008, 0.02)), level=(-18, -6))

    # And the drained mud's fine seething: very short, very high specks of noise. It also keeps the loop's seam
    # clean after encoding. A bed whose energy is mostly in the middle band (the water) and has almost nothing
    # over 8 kHz failed the `seam` check after encoding under one seed in four tried (the source loop was clean):
    # the two sides of the seam are coded 30 s apart, and the codec's error is large next to how little such a
    # signal moves from one sample to the next. This layer is about 4% of the energy; with it an estimate of how
    # often the encoded seam fails fell from about the half to the forest day bed's rate.
    seethe = lambda r: noise_burst(r, r.uniform(0.001, 0.003), lo=6000, hi=14000, attack=0.0003, release=0.001)
    fizz = scatter(s.n, s.rng("fizz"), 9000, seethe, level=(-20, -4))

    # The insect whine: a few high wavering tones, slightly apart, each side its own set, the level wandering a
    # little; under them a band of hiss pulsing too fast to count.
    def insect(side, base):
        r = s.rng("whine-" + side)
        return apply(whine(s.n, r, [base * r.uniform(0.98, 1.02) * k for k in (1.0, 1.13, 1.31)]),
                     drift(r, s.seconds, every=6.0, lo=0.55, hi=0.9))
    whine_pair = stereo(insect("a", 3300), insect("b", 3420), width=0.8)
    buzz_level = drift(s.rng("buzz"), s.seconds, every=6.0, lo=0.6, hi=0.9)
    pulse = [0.55 + 0.45 * math.sin(2 * math.pi * 140 * i / s.rate) ** 2 for i in range(s.n)]
    buzz = stereo(*[apply([a * b for a, b in zip(bandpass(white(s.n, s.rng("buzz-" + side)), 5200, 3.0), pulse)],
                          buzz_level) for side in "ab"], width=0.85)

    return mix((air, -6), (slosh, 0), (gurgle, -10), (mud, -14), (pops, -16), (whine_pair, -9), (buzz, -10),
               (fizz, -2))


def night(s):
    # The tide, slower and a little darker.
    slosh, gurgle = tide(s, "tide", 7.0, 0.55, 0.9, (380, 1000))

    # Snapping shrimp: a fine, bright crackle of very short clicks, uniform and dense, like fat in a pan far off.
    shrimp_click = lambda r: noise_burst(r, r.uniform(0.0015, 0.004), lo=2500, hi=r.uniform(7000, 12000),
                                         attack=0.0003, release=0.001)
    shrimp = scatter(s.n, s.rng("shrimp"), 14000, shrimp_click, level=(-22, -4), pan=(-1, 1))

    # A thicker insect chorus: katydid-like callers, each a short buzzy pulse train repeated on its own rate,
    # fading in and out on its own, so the mass thins and fills without a beat that comes round.
    def katydid(r):
        hz = r.uniform(2600, 4200)
        pulses, each = r.randint(3, 6), r.uniform(0.012, 0.02)
        call = seq(*[seq(tone(each, hz, ((1, 1.0), (2, 0.3), (3, 0.12)), attack=0.002, release=0.006),
                         silence(each * 0.7)) for _ in range(pulses)])
        call = distant(call, r.uniform(0.15, 0.7))
        return lambda r2: gain(call, r2.uniform(-2, 0))
    insects = chorus(s.n, s.rng("katydids"), voices=34, voice=katydid, rate=(1.6, 3.4), jitter=0.08,
                     level=(-10, 0), pan=(-0.95, 0.95), presence=(0.2, 1.0), every=5.0)

    # Under it the steady whine stays, lower and softer than by day.
    def insect(side, base):
        r = s.rng("whine-" + side)
        return apply(whine(s.n, r, [base * r.uniform(0.98, 1.02) * k for k in (1.0, 1.21)]),
                     drift(r, s.seconds, every=7.0, lo=0.6, hi=0.9))
    whine_pair = stereo(insect("a", 2400), insect("b", 2480), width=0.8)

    return mix((slosh, -1), (gurgle, -14), (shrimp, -11), (insects, -6), (whine_pair, -18))


def cues(s):
    r = s.rng      # r("name") is a new fixed source each call; a cue that draws in a loop keeps one
    crab, splash, rattle, frog, bat = r("crab"), r("splash-settle"), r("rattle"), r("frog"), r("bat")
    return [
        # A fiddler crab's claw clicks: a few quick dry clicks, irregular, close by on the mud. Sharp clicks are
        # bent by the build's peak limiter, so their loudest 100 ms comes out about 8 dB under other cues': level 0.
        cue("crab", space(seq(*[seq(knock(crab, crab.uniform(2600, 3400), 0.03, q=5.0, body=0.1),
                                    silence(crab.uniform(0.04, 0.16))) for _ in range(6)]),
                          r("crab-space"), 0.3, 0.1),
            beds=["day"], every=[20, 55], level=0, spread=0.7),

        # A kingfisher-like rattle: a run of short, rough, bright notes, dropping a little, from across the water.
        cue("rattle", space(distant(seq(*[seq(tone(0.032, (3600 - 25 * i, 3300 - 25 * i),
                                                   ((1, 1.0), (2, 0.5), (3, 0.25)), attack=0.003, release=0.012,
                                                   breath=0.25, rng=rattle),
                                              silence(0.028)) for i in range(14)]), 0.25),
                            r("rattle-space"), 0.6, 0.2),
            beds=["day"], every=[30, 80], level=-2, spread=0.9),

        # A drop falling from a leaf into still water: a bright plip and a smaller one after it. Day and night.
        cue("drip", space(seq(bubble(r("drip-a"), 1300, 1700, (0.02, 0.03)), silence(0.11),
                              gain(bubble(r("drip-b"), 1800, 2200, (0.012, 0.02)), -8)), r("drip-space"), 0.5, 0.2),
            beds=["day", "night"], every=[15, 45], level=-5, spread=0.8),

        # A mudskipper flopping: a soft wet slap on the mud, a second smaller one, a tick of mud.
        cue("mudskipper", seq(noise_burst(r("flop-a"), 0.06, lo=250, hi=2500, attack=0.002, release=0.05, curve=2.0),
                              silence(0.18),
                              gain(noise_burst(r("flop-b"), 0.04, lo=300, hi=3000, attack=0.002, release=0.035,
                                               curve=2.0), -5),
                              silence(0.07), gain(tick(r("flop-c")), -10)),
            beds=["day"], every=[40, 100], level=-5, spread=0.7),

        # A heron, far off over the water: two hoarse low calls.
        cue("heron", space(distant(seq(caw(r("heron-a"), 340, 0.38), silence(0.5),
                                       caw(r("heron-b"), 320, 0.3)), 0.6), r("heron-space"), 1.0, 0.3),
            beds=["day"], every=[45, 120], level=-6, spread=1.0),

        # A night heron's "quock": one short barked call, flat and abrupt, now and then a second.
        cue("quock", space(distant(seq(caw(r("quock-a"), 520, 0.16), silence(0.9), gain(caw(r("quock-b"), 500, 0.14), -3)),
                                   0.35), r("quock-space"), 0.9, 0.28),
            beds=["night"], every=[30, 90], level=-3, spread=0.9),

        # A splash among the roots: a fish or something larger, then the water settling in bubbles.
        cue("splash", seq(noise_burst(r("splash"), 0.18, lo=300, hi=5000, attack=0.004, release=0.15, curve=2.2),
                          *[gain(seq(silence(splash.uniform(0.03, 0.09)), bubble(splash, 400, 1200)),
                                 -splash.uniform(6, 16)) for _ in range(9)]),
            beds=["night"], every=[35, 100], level=-5, spread=0.8),

        # A tree frog: a nasal "quank", said four times, the last softer.
        cue("tree-frog", space(seq(*[seq(gain(croak(frog, 1150, 0.12, pulse=90), -2 * max(0, i - 2)),
                                         silence(0.22)) for i in range(4)]), r("frog-space"), 0.5, 0.2),
            beds=["night"], every=[20, 60], level=-3, spread=0.8),

        # A bat flying past: a quick flutter of soft wing beats, swelling and fading, with a faint squeak.
        cue("bat", overlay(seq(*[seq(gain(noise_burst(bat, 0.022, lo=400, hi=3500, attack=0.004, release=0.015),
                                          -18 * abs(i - 9) / 9), silence(0.045)) for i in range(19)]),
                           gain(chirp(0.012, 9000, 7000), -14), 0.6),
            beds=["night"], every=[40, 110], level=-6, spread=1.0),
    ]
