"""Farmland: fields, orchards, barns and hedgerows.

A soft backdrop, not a portrait. Day is open air over the fields: a low, even breath of breeze with a warm body in
the low middle (no canopy to roar, unlike the forest's wind), the faintest brush of crops, a tractor fields away
that is felt more than heard, and a hedgerow of sparrows so far off they are only a texture. Night is quiet and
wide: still low air, the hollow hush of a barn's stillness, and a light chorus of field crickets, lower in pitch
than the forest's and all far off. Anything you could pick out as one thing is a cue, and cues are rare (about one
a minute or less, most far off), each bed with one hero: a far rooster by day, a barn owl by night.
"""
from lib import *


def day(s):
    # The breeze: a slow, shallow wandering with small gusts (about 4 dB from lull to swell, as the forest's), over
    # a floor so a lull is quieter, never silent.
    calm = drift(s.rng("breeze"), s.seconds, every=6.0, lo=0.0, hi=0.45)
    g = gusts(s.rng("gusts"), s.seconds, count=7, rise=(3.0, 5.0), fall=(4.0, 8.0), size=(0.06, 0.12))
    breeze = [0.6 + 0.4 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.5))]

    # Air over open ground, the main body: pink noise from about 200 Hz up to a cutoff that follows the breeze
    # between 500 Hz and 1.3 kHz. The first version opened it to 2.2 kHz and the day was the brightest of the
    # eleven; kept here in the band a phone speaker plays, so the bed has a body there.
    air = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("air-" + side)), scale(breeze, 500, 1300)), 200),
                         breeze) for side in "ab"], width=0.8)

    # Under it, a little dark warmth: brown noise below about 300 Hz, so the field is not thin.
    warmth = stereo(*[apply(lowpass(brown(s.n, s.rng("warm-" + side), corner=80), 300), breeze) for side in "ab"],
                    width=0.6)

    # The crops: a faint, dull brush of stalks (fewer and duller puffs than the first version's, 1.2 to 4 kHz),
    # following a softened breeze and never stopping.
    stalk = lambda r: noise_burst(r, r.uniform(0.01, 0.04), lo=1200, hi=r.uniform(2800, 4000), attack=0.004,
                                  release=0.02)
    crops = scatter(s.n, s.rng("crops"), 2500, stalk, level=(-8, 0), pan=(-1, 1),
                    follow=[0.5 + 0.5 * w for w in smooth(breeze, 2.5)], depth=1.0)

    # The tractor, fields away: narrow bands of brown noise at an engine's firing rate and its harmonics, so it
    # wavers a little, as an engine under load does, but never starts or stops. The upper two (216 and 288 Hz)
    # are what a phone speaker can carry of it. Its level drifts very slowly (a far engine turning at a headland).
    far = drift(s.rng("engine"), s.seconds, every=9.0, lo=0.75, hi=1.0)
    engine = mix(*[(stereo(*[apply(bandpass(brown(s.n, s.rng("engine-%d-%s" % (hz, side)), corner=40), hz, q=9), far)
                             for side in "ab"], width=0.3), lvl)
                   for hz, lvl in ((72, 0), (144, -4), (216, -8), (288, -12))])

    # The hedgerow: thirty sparrows, all a long way off and dulled by distance, each giving one or two quick
    # chips over and over at its own rate. With this many, this far and this quiet, no one chip stands out.
    def sparrow(r):
        hz = r.uniform(3200, 4600)
        notes = r.randint(1, 2)
        call = seq(*[seq(chirp(r.uniform(0.025, 0.05), hz * r.uniform(1.05, 1.2), hz * r.uniform(0.8, 0.95)),
                         silence(r.uniform(0.03, 0.06))) for _ in range(notes)])
        call = distant(call, r.uniform(0.7, 0.9))
        return lambda r2: gain(call, r2.uniform(-3, 0))
    hedge = chorus(s.n, s.rng("hedge"), voices=30, voice=sparrow, rate=(0.4, 1.0), jitter=0.3,
                   level=(-8, 0), pan=(-0.9, 0.9), presence=(0.3, 1.0), every=6.0)

    return mix((air, 0), (warmth, -10), (engine, -9), (crops, -16), (hedge, -22))


def night(s):
    # Still, wide air: low and dark, barely moving.
    calm = drift(s.rng("calm"), s.seconds, every=7.0, lo=0.6, hi=0.85)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=80), scale(calm, 160, 320)), calm)
                   for side in "ab"], width=0.85)

    # The barn's stillness: a faint hollow hush in the low middle, as of air in a large wooden room nearby.
    hush_level = drift(s.rng("hush"), s.seconds, every=8.0, lo=0.7, hi=1.0)
    hush = stereo(*[apply(band(pink(s.n, s.rng("hush-" + side)), 220, 900), hush_level) for side in "ab"], width=0.5)

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

    # Wide open sky: a faint, even breath of air above the fields, kept under 3 kHz.
    sky_level = drift(s.rng("sky"), s.seconds, every=8.0, lo=0.75, hi=1.0)
    sky = stereo(*[apply(band(pink(s.n, s.rng("sky-" + side)), 700, 3000), sky_level) for side in "ab"], width=0.9)

    return mix((air, -2), (hush, -3), (sky, -10), (shimmer, -18), (crickets, -9))


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
    """A barn owl's screech, softened for a hero: a long breathy rasp with a faint pitch in it, rising slowly
    and falling away, kept under about 3.5 kHz and dulled by distance."""
    hiss = noise_burst(r, 1.3, lo=1200, hi=3500, attack=0.2, release=0.6, curve=1.5)
    voice = tone(1.3, (2300, 1900), harmonics=((1, 1.0), (2, 0.2)), attack=0.2, release=0.6, curve=1.5)
    return distant(add(hiss, gain(voice, -10)), 0.6)


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
    # Rare and mostly far: each bed's hero comes every 90 to 240 s, the others every 3 to 15 minutes, so a
    # listener hears about one event a minute or less. The hero sits at -3; everything else is `distant` at -6
    # to -9. The gate's latch and creak are sharp, so they are the farthest and rarest.
    r = s.rng
    return [
        # Day's hero: a rooster far across the yard.
        cue("rooster", space(rooster(r("rooster")), r("rooster-space"), 1.0, 0.3),
            beds=["day"], every=[90, 240], level=-3, spread=0.9),
        cue("cow", space(distant(moo(r("cow")), 0.3), r("cow-space"), 1.0, 0.3),
            beds=["day"], every=[180, 480], level=-6, spread=1.0),
        cue("hens", space(distant(hens(r("hens")), 0.4), r("hens-space"), 0.6, 0.2),
            beds=["day"], every=[240, 600], level=-7, spread=0.7),
        cue("sheep-bell", space(distant(sheep_bell(r("sheep-bell")), 0.4), r("sheep-bell-space"), 0.8, 0.25),
            beds=["day"], every=[240, 600], level=-7, spread=0.9),
        # The gate's latch, a field away, by day and by night.
        cue("gate-latch", distant(space(latch(r("latch")), r("latch-space"), 0.6, 0.3), 0.7),
            beds=["day", "night"], every=[300, 900], level=-9, spread=0.7),

        # Night's hero: a barn owl's screech, softened and some way off.
        cue("barn-owl", space(screech(r("owl")), r("owl-space"), 1.0, 0.3),
            beds=["night"], every=[90, 240], level=-3, spread=0.8),
        cue("dog", space(bark(r("dog")), r("dog-space"), 1.2, 0.35),
            beds=["night"], every=[240, 720], level=-8, spread=1.0),
        cue("gate-creak", distant(space(creak(r("creak"), 1.3, rate=(20, 50), hz=(500, 1300), q=7), r("creak-space"),
                                        0.6, 0.3), 0.6),
            beds=["night"], every=[300, 900], level=-8, spread=0.7),
        cue("horse", space(distant(snort(r("horse")), 0.4), r("horse-space"), 0.6, 0.25),
            beds=["night"], every=[180, 600], level=-6, spread=0.6),
    ]
