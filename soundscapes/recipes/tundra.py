"""Tundra: moss, lichen and bog pools on cold open ground.

Day is a wide, low wind over open moss with nothing standing up to break it, so it is round and dark (no
whistle, no leaves: wind over ice, thin and high, is the snowfield's; only a faint hiss over the moss), a
bog pool's faint trickle somewhere
near, and in summer a thin haze of mosquitoes. Night is the same wind lower and slower, and little else: the
emptiness is the point. Birds, a far wolf-like voice, a frost tick and the bog's bubbles are cues.
"""
from lib import *


def buzz(n, rng, hz, q=35.0):
    """One far mosquito's whine: white noise through narrow resonances at its wing-beat and three harmonics, so
    it wavers in pitch and level by itself. (Steady sine tones loop exactly too, but a stack of partials has a
    crest that can make the check's `seam` measure read high; noise through filters behaves like the rest.)"""
    return set_rms(add(*[gain(bandpass(white(n, rng), hz * k, q), d) for k, d in ((1, 0), (2, -4), (3, -7), (4, -11))]))


def wind(s, name, every, lo, hi, body_hz, breath_hz, gust_count):
    """The open wind: a dark body and a rounder breath above it, both wandering slowly with a few small, long
    gusts on top. The breath's cutoff stays under about 900 Hz, so it is a wide low rush and never a whistle."""
    calm = drift(s.rng(name), s.seconds, every=every, lo=lo, hi=hi)
    g = gusts(s.rng(name + "-gusts"), s.seconds, count=gust_count, rise=(3.0, 5.0), fall=(4.5, 8.0), size=(0.06, 0.14))
    w = [0.5 + 0.5 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 2.0))]
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng(name + "-body-" + side), corner=60), scale(w, *body_hz)), w)
                    for side in "ab"], width=0.75)
    breath = stereo(*[apply(lowpass(moving_lowpass(pink(s.n, s.rng(name + "-breath-" + side)), scale(w, *breath_hz)),
                                    900), [v ** 1.4 for v in w]) for side in "ab"], width=0.85)
    return body, breath, w


def grass_hiss(s, name, w):
    """A faint broadband hiss of air over the moss and lichen, following the wind: about 6% of the bed's energy,
    all over 4 kHz, with nothing tonal in it (so not the snowfield's whistle). It is there for the codec too.
    Without it, a bed with almost nothing over 2 kHz decoded with a step or a kink at the loop seam (the check's
    `seam` read 1.8 to 1.9 after encoding while the source loop read 0.25): the two sides of the seam are coded
    30 s apart, and the codec's error is large next to how little a dark signal moves from one sample to the
    next. Some high texture moves enough to cover it, as the leaves do in the forest."""
    return stereo(*[apply(lowpass(highpass(pink(s.n, s.rng(name + "-" + side)), 4000), 14000), w) for side in "ab"],
                  width=0.9)


def bog_drop(r):
    """One small sound of a bog pool trickling: a soft low blip of water."""
    d = r.uniform(0.02, 0.06)
    f = r.uniform(350, 900)
    return tone(d, (f, f * r.uniform(1.3, 1.7)), ((1, 1.0), (2, 0.08)), attack=0.003, release=d * 0.8, curve=2.0)


def day(s):
    body, breath, w = wind(s, "wind", 6.0, 0.25, 0.7, (150, 420), (350, 750), 6)

    # The bog pool: a faint trickle of many small drops, steady, close to the ground and to one side.
    trickle = scatter(s.n, s.rng("trickle"), 3500, bog_drop, level=(-18, -4), pan=(-0.7, 0.2))

    # The mosquito haze: three whines a little apart, far enough off to be a haze rather than a mosquito; each
    # side its own set, each fading in and out on its own.
    def mosquitoes(side):
        r = s.rng("haze-" + side)
        return add(*[apply(buzz(s.n, r, r.uniform(480, 680)), drift(r, s.seconds, every=5.0, lo=0.2, hi=0.8))
                     for _ in range(3)])
    mosq = stereo(mosquitoes("a"), mosquitoes("b"), width=0.9)

    return mix((body, 0), (breath, -4), (trickle, -15), (mosq, -17), (grass_hiss(s, "hiss", w), -6))


def night(s):
    # Lower and slower: the knots further apart, the cutoffs down, fewer gusts, no water and no insects. A faint
    # far hush keeps a little air above the rumble so the bed is not only a pressure.
    body, breath, w = wind(s, "wind", 8.5, 0.3, 0.6, (110, 280), (220, 480), 3)
    hush_level = drift(s.rng("hush"), s.seconds, every=9.0, lo=0.5, hi=0.9)
    hush = stereo(*[apply(band(pink(s.n, s.rng("hush-" + side)), 600, 2200), hush_level) for side in "ab"], width=0.9)
    return mix((body, 0), (breath, -6), (hush, -24), (grass_hiss(s, "hiss", w), -8))


def cues(s):
    r = s.rng      # r("name") is a new fixed source each call; a cue that draws in a loop keeps one
    ptarmigan, geese, frost = r("ptarmigan"), r("geese"), r("frost")
    return [
        # A ptarmigan-like call: a few low grating "kok"s, quickening into a dry rattle.
        cue("ptarmigan", space(distant(seq(*[seq(croak(ptarmigan, ptarmigan.uniform(380, 440), 0.08, pulse=70),
                                                 silence(0.32 * 0.72 ** i)) for i in range(7)],
                                           churr(ptarmigan, 0.5, hz=400, pulse=(28, 34), shifts=1)), 0.3),
                               r("ptarmigan-space"), 0.8, 0.25),
            beds=["day"], every=[30, 90], level=-3, spread=0.9),

        # Geese, far off and passing: two voices honking, out of step, dull with distance.
        cue("geese", space(distant(_geese(geese), 0.7), r("geese-space"), 1.1, 0.3),
            beds=["day"], every=[50, 140], level=-6, spread=1.0),

        # A plover's plaintive whistle: a pure falling "pyuu", twice.
        cue("plover", space(seq(*[seq(tone(0.55, [(0.0, 2450), (0.25, 2650), (1.0, 2050)], ((1, 1.0), (2, 0.03)),
                                           attack=0.03, release=0.3, vibrato=(7, 0.004)), silence(0.75))
                                  for _ in range(2)]), r("plover-space"), 0.9, 0.25),
            beds=["day"], every=[25, 70], level=-3, spread=0.9),

        # A mosquito passing near the ear: a buzz that swells and falls in pitch as it goes by.
        cue("mosquito", tone(1.8, (700, 590), ((1, 1.0), (2, 0.6), (3, 0.4), (4, 0.25)), attack=0.8, release=0.9,
                             vibrato=(17, 0.012)),
            beds=["day"], every=[40, 110], level=-6, spread=1.0),

        # A bubble rising out of the bog: a soft low gloop and a smaller one. Day and night.
        cue("bog-bubble", seq(tone(0.13, (140, 360), ((1, 1.0), (2, 0.2)), attack=0.006, release=0.1, curve=2.0),
                              silence(0.16),
                              gain(tone(0.08, (200, 430), ((1, 1.0), (2, 0.15)), attack=0.004, release=0.06, curve=2.0),
                                   -7)),
            beds=["day", "night"], every=[30, 90], level=-5, spread=0.7),

        # A far wolf-like voice: one long soft rising and falling tone, a long way off. Not a howl up close.
        cue("far-wolf", space(distant(tone(2.7, [(0.0, 360), (0.25, 465), (0.7, 445), (1.0, 320)],
                                           ((1, 1.0), (2, 0.22), (3, 0.06)), attack=0.45, release=1.1,
                                           vibrato=(5, 0.006), breath=0.04, rng=r("wolf")), 0.7),
                              r("wolf-space"), 1.0, 0.35),
            beds=["night"], every=[60, 160], level=-6, spread=1.0),

        # A snowy owl's low bark: two hoarse "kraw"s, not a hoot.
        cue("owl-bark", space(distant(seq(caw(r("owl-a"), 410, 0.2), silence(0.45), caw(r("owl-b"), 390, 0.18)), 0.45),
                              r("owl-space"), 0.8, 0.28),
            beds=["night"], every=[40, 110], level=-4, spread=0.9),

        # Frost: a tiny bright tick in the cold moss, and a fainter one. Faint, but clicks come out of the build's
        # peak limiter about 8 dB under other cues' loudest 100 ms, so its level is higher than it reads.
        cue("frost-tick", space(seq(knock(frost, 5200, 0.03, q=6.0, body=0.0), silence(frost.uniform(0.15, 0.4)),
                                    gain(knock(frost, 6100, 0.025, q=6.0, body=0.0), -8)), r("frost-space"), 0.3, 0.12),
            beds=["night"], every=[20, 60], level=-4, spread=0.8),

        # A far loon-like call: a long wavering wail rising and settling, across open water a long way off.
        cue("loon", space(distant(tone(2.6, [(0.0, 680), (0.3, 1040), (0.6, 990), (1.0, 900)], ((1, 1.0), (2, 0.14)),
                                       attack=0.25, release=0.8, vibrato=(6, 0.01)), 0.6),
                          r("loon-space"), 1.0, 0.3),
            beds=["night"], every=[50, 140], level=-5, spread=1.0),
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
