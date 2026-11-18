"""Farmland: fields, orchards, barns and hedgerows.

A soft backdrop, not a portrait. Day is open air over the fields: a low, even breath of breeze with a warm body in
the low middle (no canopy to roar, unlike the forest's wind), the faintest brush of crops, and a tractor fields
away that is felt more than heard. Night is quiet and wide: still low air, the hollow hush of a barn's stillness,
and the faint shimmer of field crickets all far off, lower in pitch than the forest's. A bed holds only continuous
texture. Anything you could pick out as one thing is a cue, and cues are rare (about one
a minute or less, most far off), each bed with one hero: a far rooster by day, a barn owl by night.
"""
from lib import *


def day(s):
    # The breeze: a slow, shallow wandering, a new level about every 10 s, about 2 dB deep, and no gusts (the
    # owner, 2026-11-17: the beds were too active).
    breeze = scale(drift(s.rng("breeze"), s.seconds, every=10.0), 0.78, 1.0)

    # Air over open ground, the main body: pink noise from about 200 Hz up to a cutoff that follows the breeze
    # between 700 Hz and 1.2 kHz. The first version opened it to 2.2 kHz and the day was the brightest of the
    # eleven; kept here in the band a phone speaker plays, so the bed has a body there.
    air = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("air-" + side)), scale(breeze, 700, 1200)), 200),
                         breeze) for side in "ab"], width=0.8)

    # Under it, a little dark warmth: brown noise below about 300 Hz, so the field is not thin.
    warmth = stereo(*[apply(lowpass(brown(s.n, s.rng("warm-" + side), corner=80), 300), breeze) for side in "ab"],
                    width=0.6)

    # The crops as a whole: a faint, dull, continuous brush from 1.2 to 3.5 kHz on its own slow wandering (the
    # second version made it of puffs, a crackle).
    crop_level = scale(drift(s.rng("crops"), s.seconds, every=12.0), 0.8, 1.0)
    crops = stereo(*[apply(band(pink(s.n, s.rng("crops-" + side)), 1200, 3500), crop_level) for side in "ab"],
                   width=0.9)

    # The tractor, fields away: narrow bands of brown noise at an engine's firing rate and its harmonics, so it
    # wavers a little, as an engine under load does, but never starts or stops. The upper two (216 and 288 Hz)
    # are what a phone speaker can carry of it. Its level drifts very slowly and hardly at all. The second
    # version's hedgerow of thirty chipping sparrows is gone: a chip is an event, however far.
    far = drift(s.rng("engine"), s.seconds, every=13.0, lo=0.85, hi=1.0)
    engine = mix(*[(stereo(*[apply(bandpass(brown(s.n, s.rng("engine-%d-%s" % (hz, side)), corner=40), hz, q=9), far)
                             for side in "ab"], width=0.3), lvl)
                   for hz, lvl in ((72, 0), (144, -4), (216, -8), (288, -12))])

    return mix((air, 0), (warmth, -10), (engine, -12), (crops, -17))


def night(s):
    # Still, wide air: low and dark, barely moving.
    calm = scale(drift(s.rng("calm"), s.seconds, every=12.0), 0.85, 1.0)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=80), scale(calm, 180, 280)), calm)
                   for side in "ab"], width=0.85)

    # The barn's stillness: a faint hollow hush in the low middle, as of air in a large wooden room nearby.
    hush_level = scale(drift(s.rng("hush"), s.seconds, every=12.0), 0.82, 1.0)
    hush = stereo(*[apply(band(pink(s.n, s.rng("hush-" + side)), 220, 900), hush_level) for side in "ab"], width=0.5)

    # Field crickets, all far out in the fields: too many and too far to tell apart, a faint even shimmer at their
    # pitch (2.9 to 3.9 kHz, lower than the forest's), wandering slowly. No caller of its own (the second
    # version's 40 chirping callers were the busiest thing in the bed; a chirp is a cue's business).
    shimmer_level = scale(drift(s.rng("shimmer"), s.seconds, every=12.0), 0.8, 1.0)
    shimmer = stereo(*[apply(band(white(s.n, s.rng("shimmer-" + side)), 2900, 3900), shimmer_level)
                       for side in "ab"], width=0.9)

    # Wide open sky: a faint, even breath of air above the fields, kept under 3 kHz.
    sky_level = scale(drift(s.rng("sky"), s.seconds, every=13.0), 0.84, 1.0)
    sky = stereo(*[apply(band(pink(s.n, s.rng("sky-" + side)), 700, 3000), sky_level) for side in "ab"], width=0.9)

    return mix((air, -2), (hush, -3), (sky, -10), (shimmer, -14))


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
