"""Mangrove: tidal forest, roots, mud and brackish water.

A soft backdrop, not a portrait. Day is slow tide water among the roots, low and warm: a dark slosh with a quiet
gurgle in it, in close, humid, still air, and a faint far haze of insects at most. Night is the same tide, slower
and darker, with a far, thin chorus of insects over it. The mud's ticks, the birds, a drip, a splash, a frog and a
bat are cues, and cues are rare: about one a minute or less, most of them far off. Each bed has one hero (a dove's
soft coo by day, a night heron's "quock" by night), allowed a little nearer.

The first version had a high insect whine, a pulsing buzz, mud ticks and (by night) a snapping-shrimp crackle in its
beds; the owner found the beds harsh, so all of that is gone and the beds are water, low and slow.
"""
from lib import *


def bubble(r, lo=200, hi=600, seconds=(0.02, 0.06)):
    """A small, soft rising blip of water among roots."""
    d = r.uniform(*seconds)
    f = r.uniform(lo, hi)
    return tone(d, (f, f * r.uniform(1.3, 1.7)), ((1, 1.0), (2, 0.06)), attack=0.006, release=d * 0.7, curve=1.5)


def tide(s, name, every, cutoff, gurgle_count):
    """The water among the roots: brown and pink noise kept low (the slosh's cutoff wanders slowly within
    `cutoff`, never above about 800 Hz), and a quiet gurgle of small low bubbles that is a little busier where the
    water moves more. Both have a floor, so a still moment of water never empties into a landmark."""
    flow = drift(s.rng(name), s.seconds, every=every, lo=0.0, hi=1.0)
    level = [0.7 + 0.3 * v for v in flow]           # about 3 dB from slack to moving water
    deep = stereo(*[apply(moving_lowpass(brown(s.n, s.rng(name + "-deep-" + side), corner=80), scale(flow, 160, 320)),
                          level) for side in "ab"], width=0.7)
    slosh = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng(name + "-" + side)), scale(flow, *cutoff)), 150),
                           level) for side in "ab"], width=0.75)
    gurgle = scatter(s.n, s.rng(name + "-gurgle"), gurgle_count, bubble, level=(-14, -2), pan=(-0.9, 0.9),
                     follow=[0.5 + 0.5 * v for v in smooth(flow, 2.0)], depth=0.6)
    return deep, slosh, gurgle


def haze(s, name, centre, depth):
    """Insects too far away to tell apart: a band of noise round `centre`, its level wandering slowly between
    `depth` and 1. Faint by design: it is there only to say the air is alive."""
    lvl = drift(s.rng(name), s.seconds, every=7.0, lo=depth, hi=1.0)
    return stereo(*[apply(lowpass(bandpass(white(s.n, s.rng(name + "-" + side)), centre, 2.0), centre * 1.3), lvl)
                    for side in "ab"], width=0.9)


def day(s):
    # Humid stillness under the water: a dark, barely moving body of air.
    still = drift(s.rng("still"), s.seconds, every=7.0, lo=0.8, hi=0.95)
    air = stereo(*[apply(lowpass(brown(s.n, s.rng("air-" + side), corner=70), 200), still) for side in "ab"],
                 width=0.6)
    deep, slosh, gurgle = tide(s, "tide", 6.0, (350, 800), 2500)
    return mix((air, -4), (deep, -2), (slosh, 0), (gurgle, -14), (haze(s, "haze", 3000, 0.5), -30))


def night(s):
    # The tide slower and darker; over it a thin, far insect chorus: short soft pulse trains, all of them some
    # way off, each fading in and out on its own, so the mass thins and fills with no beat that comes round.
    deep, slosh, gurgle = tide(s, "tide", 8.0, (260, 600), 1800)

    def katydid(r):
        hz = r.uniform(2400, 3600)
        pulses, each = r.randint(2, 4), r.uniform(0.014, 0.022)
        call = seq(*[seq(tone(each, hz, ((1, 1.0), (2, 0.15)), attack=0.004, release=0.008), silence(each * 0.8))
                     for _ in range(pulses)])
        call = distant(call, r.uniform(0.55, 0.9))
        return lambda r2: gain(call, r2.uniform(-2, 0))
    insects = chorus(s.n, s.rng("katydids"), voices=18, voice=katydid, rate=(0.8, 1.8), jitter=0.1,
                     level=(-10, 0), pan=(-0.95, 0.95), presence=(0.2, 1.0), every=6.0)

    return mix((deep, 0), (slosh, -1), (gurgle, -16), (insects, -9), (haze(s, "haze", 2800, 0.5), -26))


def coo(r):
    """A dove's soft "coo-cooo, coo": round low hoots, the second long."""
    return seq(hoot(520, 0.28, 0.95, rng=r), silence(0.12), hoot(540, 0.6, 0.9, rng=r), silence(0.35),
               hoot(510, 0.3, 0.94, rng=r))


def cues(s):
    # Rare and mostly far: each bed's hero comes every 90 to 240 s, the others every 3 to 10 minutes or rarer, so a
    # listener hears about one event a minute or less. Every cue file's loudest 100 ms is 6 dB over a nominal
    # bed's RMS: the hero sits at -3, everything else at -6 to -9 and `distant`. Nothing sharp is near.
    r = s.rng      # r("name") is a new fixed source each call; a cue that draws in a loop keeps one
    mud, splash, frog, bat = r("mud"), r("splash-settle"), r("frog"), r("bat")
    return [
        # Day's hero: a dove cooing somewhere in the canopy over the water.
        cue("dove", space(distant(coo(r("dove")), 0.3), r("dove-space"), 0.8, 0.25),
            beds=["day"], every=[90, 240], level=-3, spread=0.9),

        # A kingfisher-like rattle across the water: a run of short soft notes, dropping a little, far off.
        cue("rattle", space(distant(seq(*[seq(tone(0.035, (3300 - 25 * i, 3050 - 25 * i), ((1, 1.0), (2, 0.3)),
                                                   attack=0.006, release=0.015), silence(0.03)) for i in range(12)]),
                                    0.7), r("rattle-space"), 0.8, 0.3),
            beds=["day"], every=[180, 480], level=-7, spread=0.9),

        # The mud: a few dull ticks and a soft pop as it drains, a little way off.
        cue("mud", distant(seq(*[seq(knock(mud, mud.uniform(900, 1400), 0.03, q=3.0, body=0.0),
                                     silence(mud.uniform(0.12, 0.4))) for _ in range(3)],
                               bubble(mud, 250, 450, (0.04, 0.06))), 0.6),
            beds=["day"], every=[240, 600], level=-8, spread=0.7),

        # A heron, far off over the water: two hoarse low calls.
        cue("heron", space(distant(seq(caw(r("heron-a"), 340, 0.38), silence(0.5), caw(r("heron-b"), 320, 0.3)), 0.75),
                           r("heron-space"), 1.0, 0.3),
            beds=["day"], every=[300, 900], level=-8, spread=1.0),

        # A drop falling from a leaf into still water, a little way off. Day and night.
        cue("drip", space(distant(seq(bubble(r("drip-a"), 900, 1200, (0.025, 0.035)), silence(0.14),
                                      gain(bubble(r("drip-b"), 1100, 1400, (0.015, 0.025)), -8)), 0.5),
                          r("drip-space"), 0.6, 0.25),
            beds=["day", "night"], every=[180, 600], level=-7, spread=0.8),

        # Night's hero: a night heron's "quock", one flat barked call and now and then a softer second.
        cue("quock", space(distant(seq(caw(r("quock-a"), 480, 0.17), silence(0.9), gain(caw(r("quock-b"), 460, 0.15), -4)),
                                   0.5), r("quock-space"), 1.0, 0.3),
            beds=["night"], every=[90, 240], level=-3, spread=0.9),

        # Something slipping into the water among the roots, then the water settling in bubbles. Far.
        cue("splash", distant(seq(noise_burst(splash, 0.2, lo=200, hi=2500, attack=0.012, release=0.17, curve=2.0),
                                  *[gain(seq(silence(splash.uniform(0.04, 0.1)), bubble(splash, 250, 600)),
                                         -splash.uniform(6, 16)) for _ in range(7)]), 0.55),
            beds=["night"], every=[240, 600], level=-7, spread=0.8),

        # A tree frog some way off: a nasal "quank", three times, the last softer.
        cue("tree-frog", space(distant(seq(*[seq(gain(croak(frog, 1000, 0.12, pulse=80), -3 * max(0, i - 1)),
                                                 silence(0.3)) for i in range(3)]), 0.55), r("frog-space"), 0.6, 0.25),
            beds=["night"], every=[180, 480], level=-7, spread=0.8),

        # A bat passing: a quick soft flutter of wing beats, swelling and fading.
        cue("bat", distant(seq(*[seq(gain(noise_burst(bat, 0.024, lo=300, hi=2500, attack=0.006, release=0.016),
                                          -18 * abs(i - 9) / 9), silence(0.045)) for i in range(19)]), 0.4),
            beds=["night"], every=[300, 900], level=-8, spread=1.0),
    ]
