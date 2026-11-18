"""Tundra: moss, lichen and bog pools on cold open ground.

A soft backdrop, not a portrait. Day is a wide, low wind over open moss with nothing standing up to break it, so it
is round and dark (no whistle, no hiss, no leaves: wind over ice, thin and high, is the snowfield's), and a bog
pool's faint, even purl somewhere near. Night is the same wind lower and slower and nothing else: the emptiness is
the point. A bed holds only continuous texture. Birds, a far wolf-like voice, a frost tick and the bog's bubbles are cues, and cues are rare: about one a
minute or less, most of them far off. Each bed has one hero (a plover's plaintive whistle by day, a far loon by
night), allowed a little nearer.

The first version also had a mosquito haze in the day bed and, for the loop seam, a faint high hiss in both; the
haze went with the owner's call for a calmer backdrop, and the hiss when the build began encoding a bed in two laps.
"""
from lib import *


def wind(s, name, every, floor, body_hz, breath_hz):
    """The open wind: a dark body and a rounder breath above it, both wandering slowly and shallowly between
    `floor` and 1 (no gusts since 2026-11-17, when the owner found the beds too active). The breath's cutoff stays
    under about 800 Hz, so it is a wide low rush and never a whistle."""
    w = scale(drift(s.rng(name), s.seconds, every=every), floor, 1.0)
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng(name + "-body-" + side), corner=60), scale(w, *body_hz)), w)
                    for side in "ab"], width=0.75)
    breath = stereo(*[apply(lowpass(moving_lowpass(pink(s.n, s.rng(name + "-breath-" + side)), scale(w, *breath_hz)),
                                    800), w) for side in "ab"], width=0.85)
    return body, breath


def day(s):
    body, breath = wind(s, "wind", 10.0, 0.78, (180, 320), (400, 620))
    # The bog pool somewhere near, to one side: a faint, even purl of water in the low middle. The second version
    # made it of 3000 small drops; a drop is a blip, so the drops are the bubbles cue's alone.
    pool_level = scale(drift(s.rng("trickle"), s.seconds, every=12.0), 0.8, 1.0)
    pool = mix((pan(apply(band(pink(s.n, s.rng("trickle-a")), 350, 1000), pool_level), -0.4), 0),
               (pan(apply(band(pink(s.n, s.rng("trickle-b")), 350, 1000), pool_level), 0.1), -3))
    return mix((body, 0), (breath, -4), (pool, -17))


def night(s):
    # Lower and slower: the knots further apart, the cutoffs down, no water. A faint far hush keeps a little air
    # above the rumble so the bed is not only a pressure.
    body, breath = wind(s, "wind", 13.0, 0.85, (130, 230), (260, 420))
    hush_level = scale(drift(s.rng("hush"), s.seconds, every=13.0), 0.82, 1.0)
    hush = stereo(*[apply(band(pink(s.n, s.rng("hush-" + side)), 500, 1600), hush_level) for side in "ab"], width=0.9)
    return mix((body, 0), (breath, -6), (hush, -20))


def cues(s):
    # Rare and mostly far: each bed's hero comes every 90 to 240 s, the others every 3 to 10 minutes or rarer, so a
    # listener hears about one event a minute or less, with minutes of only wind. The hero sits at -3, everything
    # else at -6 to -9 and `distant`. Nothing sharp is near.
    r = s.rng      # r("name") is a new fixed source each call; a cue that draws in a loop keeps one
    ptarmigan, geese, frost = r("ptarmigan"), r("geese"), r("frost")
    return [
        # Day's hero: a plover's plaintive whistle, a pure falling "pyuu", twice, in the open.
        cue("plover", space(distant(seq(*[seq(tone(0.55, [(0.0, 2400), (0.25, 2600), (1.0, 2000)], ((1, 1.0), (2, 0.03)),
                                                   attack=0.05, release=0.3, vibrato=(7, 0.004)), silence(0.8))
                                          for _ in range(2)]), 0.3), r("plover-space"), 1.0, 0.3),
            beds=["day"], every=[90, 240], level=-3, spread=0.9),

        # A ptarmigan-like call well away: a few low grating "kok"s, quickening into a dry rattle.
        cue("ptarmigan", space(distant(seq(*[seq(croak(ptarmigan, ptarmigan.uniform(380, 440), 0.08, pulse=70),
                                                 silence(0.32 * 0.72 ** i)) for i in range(7)],
                                           churr(ptarmigan, 0.5, hz=400, pulse=(28, 34), shifts=1)), 0.65),
                               r("ptarmigan-space"), 0.9, 0.3),
            beds=["day"], every=[180, 480], level=-7, spread=0.9),

        # Geese, far off and passing: two voices honking, out of step, dull with distance.
        cue("geese", space(distant(_geese(geese), 0.75), r("geese-space"), 1.1, 0.3),
            beds=["day"], every=[300, 900], level=-8, spread=1.0),

        # A bubble rising out of the bog a little way off: a soft low gloop and a smaller one. Day and night.
        cue("bog-bubble", distant(seq(tone(0.14, (140, 340), ((1, 1.0), (2, 0.15)), attack=0.01, release=0.11, curve=1.5),
                                      silence(0.16),
                                      gain(tone(0.09, (190, 400), ((1, 1.0), (2, 0.1)), attack=0.008, release=0.07,
                                                curve=1.5), -7)), 0.3),
            beds=["day", "night"], every=[180, 600], level=-7, spread=0.7),

        # Night's hero: a far loon-like call, a long wavering wail rising and settling, across open water.
        cue("loon", space(distant(tone(2.6, [(0.0, 680), (0.3, 1040), (0.6, 990), (1.0, 900)], ((1, 1.0), (2, 0.14)),
                                       attack=0.3, release=0.8, vibrato=(6, 0.01)), 0.6),
                          r("loon-space"), 1.0, 0.3),
            beds=["night"], every=[90, 240], level=-3, spread=1.0),

        # A far wolf-like voice: one long soft rising and falling tone, a long way off. Not a howl up close.
        cue("far-wolf", space(distant(tone(2.7, [(0.0, 360), (0.25, 465), (0.7, 445), (1.0, 320)],
                                           ((1, 1.0), (2, 0.22), (3, 0.06)), attack=0.45, release=1.1,
                                           vibrato=(5, 0.006), breath=0.04, rng=r("wolf")), 0.75),
                              r("wolf-space"), 1.0, 0.35),
            beds=["night"], every=[300, 900], level=-7, spread=1.0),

        # A snowy owl's low bark some way off: two hoarse "kraw"s, not a hoot.
        cue("owl-bark", space(distant(seq(caw(r("owl-a"), 410, 0.2), silence(0.45), caw(r("owl-b"), 390, 0.18)), 0.6),
                              r("owl-space"), 0.9, 0.3),
            beds=["night"], every=[240, 600], level=-7, spread=0.9),

        # Frost: a tiny tick in the cold moss and a fainter one, far and rare. Sharp, so it stays at -9 (clicks also
        # come out of the build's peak limiter a few dB under other cues' loudest 100 ms).
        cue("frost-tick", space(distant(seq(knock(frost, 4200, 0.03, q=6.0, body=0.0), silence(frost.uniform(0.15, 0.4)),
                                            gain(knock(frost, 4800, 0.025, q=6.0, body=0.0), -8)), 0.5),
                                r("frost-space"), 0.4, 0.2),
            beds=["night"], every=[300, 900], level=-9, spread=0.8),
    ]


def _geese(r):
    """Two geese honking out of step: nasal two-part honks at two pitches."""
    out = silence(0.1)
    for voice, hz in enumerate((420, 360)):
        t = 0.05 + voice * 0.17
        for _ in range(5):
            f = hz * r.uniform(0.97, 1.03)
            honk = tone(0.17, [(0.0, f * 0.9), (0.3, f), (1.0, f * 0.92)],
                        ((1, 1.0), (2, 0.8), (3, 0.6), (4, 0.4), (5, 0.25)), attack=0.02, release=0.07)
            overlay(out, honk, t, r.uniform(0.6, 1.0))
            t += r.uniform(0.3, 0.45)
    return out
