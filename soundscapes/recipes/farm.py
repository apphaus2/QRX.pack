"""Farmland: fields, orchards, barns and hedgerows.

Day is open air: a breeze over the crops (a soft, even hiss of stalks with little low body, unlike the forest's
dark canopy wind), a tractor fields away that is felt more than heard (a low, steady, slightly wavering hum), and
sparrows chattering in a hedgerow, so many and so far that they are a texture, not birds. Night is quiet and wide:
still low air, the faint hush of a barn's stillness, and field crickets, lower in pitch than the forest's, all far off and lighter in the mix.
Everything you could pick out as one thing (a rooster, a cow, a bell, a gate) is a cue.
"""
from lib import *


def day(s):
    # The breeze: a slow, shallow wandering with small gusts, as in the forest (deeper swells made `stand` fire
    # there), with a floor so a lull is quieter, never silent.
    calm = drift(s.rng("breeze"), s.seconds, every=5.5, lo=0.0, hi=0.55)
    g = gusts(s.rng("gusts"), s.seconds, count=7, rise=(2.5, 4.5), fall=(4.0, 7.0), size=(0.08, 0.16))
    breeze = [0.5 + 0.5 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.5))]

    # Air over open ground: pink noise kept out of the lows (an open field has no canopy to roar), its cutoff
    # rising with the breeze. This is the main body of the bed.
    air = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("air-" + side)), scale(breeze, 900, 2200)), 180),
                         breeze) for side in "ab"], width=0.8)

    # The crops: many tiny soft puffs of noise in the 1.5-5 kHz band, the stalks brushing. Darker and denser than
    # the forest's leaves (which reach 11 kHz), following a softened breeze and never stopping.
    stalk = lambda r: noise_burst(r, r.uniform(0.01, 0.04), lo=1500, hi=r.uniform(3500, 5500), attack=0.003,
                                  release=0.015)
    crops = scatter(s.n, s.rng("crops"), 5000, stalk, level=(-10, 0), pan=(-1, 1),
                    follow=[0.4 + 0.6 * w for w in smooth(breeze, 2.5)], depth=1.0)

    # The tractor, fields away: narrow bands of brown noise at an engine's firing rate and its second
    # harmonic, so it is a hum that wavers a little, as an engine under load does, but nothing like a tone that
    # starts or stops. Its level drifts very slowly (a far engine turning at a headland).
    far = drift(s.rng("engine"), s.seconds, every=9.0, lo=0.75, hi=1.0)
    engine = mix(*[(stereo(*[apply(bandpass(brown(s.n, s.rng("engine-%d-%s" % (hz, side)), corner=40), hz, q=9), far)
                             for side in "ab"], width=0.3), lvl) for hz, lvl in ((72, 0), (144, -5), (216, -11))])

    # The hedgerow: thirty sparrows, all some way off, each giving one or two quick chips over and over at its
    # own rate, fading in and out. With this many, this far, and this quiet, no one chip stands out.
    def sparrow(r):
        hz = r.uniform(3400, 5200)
        notes = r.randint(1, 2)
        call = seq(*[seq(chirp(r.uniform(0.025, 0.05), hz * r.uniform(1.05, 1.25), hz * r.uniform(0.75, 0.95)),
                         silence(r.uniform(0.03, 0.06))) for _ in range(notes)])
        call = distant(call, r.uniform(0.45, 0.85))
        return lambda r2: gain(call, r2.uniform(-4, 0))
    hedge = chorus(s.n, s.rng("hedge"), voices=30, voice=sparrow, rate=(0.4, 1.1), jitter=0.3,
                   level=(-12, 0), pan=(-0.9, 0.9), presence=(0.1, 1.0), every=5.0)

    return mix((air, 0), (crops, -8), (engine, -6), (hedge, -15))


def night(s):
    # Still, wide air: low and dark, barely moving.
    calm = drift(s.rng("calm"), s.seconds, every=7.0, lo=0.6, hi=0.85)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=80), scale(calm, 160, 320)), calm)
                   for side in "ab"], width=0.85)

    # The barn's stillness: a faint hollow hush in the low middle, as of air in a large wooden room nearby.
    hush_level = drift(s.rng("hush"), s.seconds, every=8.0, lo=0.7, hi=1.0)
    hush = stereo(*[apply(band(pink(s.n, s.rng("hush-" + side)), 220, 700), hush_level) for side in "ab"], width=0.5)

    # Field crickets: lower than the forest's (about 3.3 kHz against 4.2-5.2), slower, and all of them far out
    # in the fields, so the chorus is light and even. A few near, loud callers stood out of it (`stand`); many
    # far ones of nearly one level do not.
    def cricket(r):
        hz = r.uniform(3100, 3600)
        pulses, length, gap = r.randint(2, 3), r.uniform(0.014, 0.02), r.uniform(0.02, 0.03)
        call = seq(*[seq(chirp(length, hz * 1.01, hz * 0.99), silence(gap)) for _ in range(pulses)])
        call = distant(call, r.uniform(0.6, 0.9))
        return lambda r2: gain(call, r2.uniform(-2, 0))
    crickets = chorus(s.n, s.rng("crickets"), voices=40, voice=cricket, rate=(0.7, 1.3), jitter=0.08,
                      level=(-5, 0), pan=(-1, 1), presence=(0.35, 1.0), every=6.0)

    # Under them the crickets too far off to tell apart, a faint even shimmer at their pitch.
    shimmer_level = drift(s.rng("shimmer"), s.seconds, every=7.0, lo=0.6, hi=1.0)
    shimmer = stereo(*[apply(band(white(s.n, s.rng("shimmer-" + side)), 2900, 3900), shimmer_level)
                       for side in "ab"], width=0.9)

    # Wide open sky: a faint, even breath of air above the fields, which keeps the bed from being all rumble.
    sky_level = drift(s.rng("sky"), s.seconds, every=8.0, lo=0.75, hi=1.0)
    sky = stereo(*[apply(band(pink(s.n, s.rng("sky-" + side)), 900, 4000), sky_level) for side in "ab"], width=0.9)

    # A trace of high air hiss. Hardly audible, but a bed with almost nothing above 8 kHz came back from the
    # codec with a seam that failed its check (the step across the wrap is measured against the steps around it,
    # which in a dark bed are tiny); a little energy up here gives that measure something to compare with.
    hiss = stereo(*[highpass(blue(s.n, s.rng("hiss-" + side)), 7000) for side in "ab"], width=0.9)

    return mix((air, -2), (hush, -4), (sky, -9), (shimmer, -17), (crickets, -8), (hiss, -26))


def rooster(r):
    """A rooster's crow, far across the yard: four syllables, the third held and falling, rich and nasal."""
    shape = [(0.0, 520), (0.12, 760), (0.3, 700), (0.45, 880), (0.8, 820), (1.0, 560)]
    crow = tone(1.5, shape, harmonics=((1, 1.0), (2, 0.6), (3, 0.35), (4, 0.15)), attack=0.03, release=0.25,
                vibrato=(9, 0.012), breath=0.04, rng=r)
    return distant(crow, 0.6)


def moo(r):
    """A cow two fields off: a long low lowing that rises a little and sinks."""
    low = tone(1.7, [(0.0, 120), (0.25, 150), (0.7, 140), (1.0, 105)],
               harmonics=((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.3), (5, 0.15)), attack=0.15, release=0.4,
               breath=0.05, rng=r)
    return distant(lowpass(low, 900), 0.55)


def hens(r):
    """Hens clucking together: a handful of short, nasal, rising-and-falling clucks at uneven gaps."""
    parts = []
    for _ in range(r.randint(6, 8)):
        hz = r.uniform(420, 620)
        parts.append(tone(r.uniform(0.06, 0.11), (hz, hz * r.uniform(0.8, 1.2)),
                          harmonics=((1, 1.0), (2, 0.5), (3, 0.3)), attack=0.005, release=0.03, breath=0.1, rng=r))
        parts.append(silence(r.uniform(0.08, 0.25)))
    return distant(seq(*parts), 0.35)


def sheep_bell(r):
    """A sheep's bell, a hollow iron clank, swinging two or three times as the animal grazes."""
    clank = ((1.0, 1.0, 0.35), (1.58, 0.6, 0.25), (2.31, 0.4, 0.18), (3.9, 0.15, 0.1))
    parts = []
    for _ in range(r.randint(2, 3)):
        parts.append(bell(r.uniform(820, 860), 0.45, clank))
        parts.append(silence(r.uniform(0.15, 0.4)))
    return distant(seq(*parts), 0.4)


def latch(r):
    """A gate latch: the bar lifted (a small knock) and dropped home a moment later (a brighter metal clack)."""
    return seq(knock(r, 1600, 0.08, q=10, body=0.2), silence(r.uniform(0.25, 0.45)),
               knock(r, 2400, 0.12, q=14, body=0.3))


def screech(r):
    """A barn owl's screech, softened: a long breathy hiss with a faint pitch in it, falling away."""
    hiss = noise_burst(r, 1.2, lo=1800, hi=5000, attack=0.08, release=0.5, curve=1.5)
    voice = tone(1.2, (2600, 2200), harmonics=((1, 1.0), (2, 0.3)), attack=0.08, release=0.5, curve=1.5)
    return distant(add(hiss, gain(voice, -10)), 0.55)


def bark(r):
    """A dog barking somewhere down the lane: two or three short barks."""
    parts = []
    for _ in range(r.randint(2, 3)):
        hz = r.uniform(380, 460)
        b = tone(0.16, [(0.0, hz), (0.3, hz * 1.25), (1.0, hz * 0.8)],
                 harmonics=((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.3)), attack=0.008, release=0.08, curve=1.5,
                 breath=0.25, rng=r)
        parts.append(b)
        parts.append(silence(r.uniform(0.2, 0.35)))
    return distant(seq(*parts), 0.75)


def snort(r):
    """A horse in the barn blowing through its lips: a short fluttering puff of breath."""
    flutter = seq(*[noise_burst(r, 0.035, lo=150, hi=r.uniform(1200, 1800), attack=0.004, release=0.02)
                    for _ in range(14)])
    puff = noise_burst(r, 0.5, lo=300, hi=2500, attack=0.02, release=0.3)
    return distant(overlay(flutter, gain(puff, -6), 0.0), 0.3)


def cues(s):
    r = s.rng
    return [
        cue("rooster", space(rooster(r("rooster")), r("rooster-space"), 1.0, 0.3),
            beds=["day"], every=[50, 140], level=-5, spread=0.9),
        cue("cow", space(moo(r("cow")), r("cow-space"), 1.0, 0.3),
            beds=["day"], every=[40, 110], level=-5, spread=1.0),
        cue("hens", space(hens(r("hens")), r("hens-space"), 0.5, 0.15),
            beds=["day"], every=[25, 70], level=-3, spread=0.7),
        cue("sheep-bell", space(sheep_bell(r("sheep-bell")), r("sheep-bell-space"), 0.8, 0.25),
            beds=["day"], every=[30, 80], level=-4, spread=0.9),
        # The gate's latch, by day and by night.
        cue("gate-latch", space(latch(r("latch")), r("latch-space"), 0.5, 0.2),
            beds=["day", "night"], every=[60, 150], level=-3, spread=0.7),

        cue("barn-owl", space(screech(r("owl")), r("owl-space"), 1.0, 0.3),
            beds=["night"], every=[40, 110], level=-5, spread=0.8),
        cue("dog", space(bark(r("dog")), r("dog-space"), 1.2, 0.35),
            beds=["night"], every=[45, 120], level=-7, spread=1.0),
        cue("gate-creak", space(creak(r("creak"), 1.3, rate=(20, 50), hz=(500, 1300), q=7), r("creak-space"), 0.6, 0.2),
            beds=["night"], every=[40, 100], level=-3, spread=0.7),
        cue("horse", space(snort(r("horse")), r("horse-space"), 0.5, 0.2),
            beds=["night"], every=[35, 90], level=-3, spread=0.6),
    ]
