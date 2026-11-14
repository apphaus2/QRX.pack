"""Marsh: reedbeds, fens and flooded grass.

A soft backdrop, not a portrait. Day is a reedbed in a light wind: a low breath of air over the open marsh and
the reeds' faint, dull rustle moving with it, slowly. Night is still air over still water, and far off a sparse,
low chorus of frogs, too distant for any one to stand out. Cues are rare and mostly far; each bed has one hero,
the sound that says "marsh" (a reed warbler's chatter by day, a bittern's boom at night).

Unlike the forest's leaves, reeds are longer, papery grains held low in the middle band, and the marsh has no
canopy rush over them: the air is lower and the rustle carries more of the bed. Unlike open water there are no
swells. The first version had a busy insect buzz and sixty frogs; both are gone from the beds.
"""
from lib import *


def day(s):
    # The wind over the reeds: a shallow wandering with small gusts, over a floor, about 4 dB from lull to swell.
    calm = drift(s.rng("wind"), s.seconds, every=6.0, lo=0.0, hi=0.45)
    g = gusts(s.rng("gusts"), s.seconds, count=7, rise=(3.0, 5.0), fall=(4.0, 8.0), size=(0.06, 0.14))
    wind = [0.6 + 0.4 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.5))]
    soft = [0.45 + 0.55 * w for w in smooth(wind, 2.0)]

    # A low body of moving air: a marsh is open and low.
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("body-" + side), corner=80), scale(wind, 160, 380)), wind)
                    for side in "ab"], width=0.7)

    # The reeds as a whole: a soft continuous hush in the low middle band, following the wind.
    hush = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("hush-" + side)), scale(wind, 700, 1400)), 250),
                          wind) for side in "ab"], width=0.8)

    # The reeds' rustle: longer, papery grains from about 700 Hz to at most 2.6 kHz, faint, a little thicker in
    # the gusts and never stopping.
    swish = lambda r: noise_burst(r, r.uniform(0.03, 0.08), lo=r.uniform(600, 900), hi=r.uniform(1800, 2600),
                                  attack=0.012, release=0.035)
    rustle = scatter(s.n, s.rng("rustle"), 2200, swish, level=(-8, 0), pan=(-1, 1), follow=soft, depth=1.0)

    return mix((body, 0), (hush, -4), (rustle, -9))


def night(s):
    # Still air over still water: a faint dark hush, barely moving.
    calm = drift(s.rng("calm"), s.seconds, every=8.0, lo=0.8, hi=1.0)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=70), scale(calm, 140, 260)), calm)
                   for side in "ab"], width=0.6)

    # The frogs, far off: low middling croakers only (no high peepers, no deep ones), each with its own pitch and
    # pulse and three calls made once that it chooses among, all well away, calling slowly; the chorus fades each
    # in and out on its own, so it keeps thinning and filling.
    def frog(r):
        hz, pulse = r.uniform(340, 560), r.uniform(22, 34)
        far = r.uniform(0.6, 0.9)
        calls = [distant(croak(r, hz * r.uniform(0.97, 1.03), r.uniform(0.2, 0.4), pulse), far) for _ in range(3)]
        return lambda r2: gain(calls[r2.randrange(3)], r2.uniform(-3, 0))
    frogs = chorus(s.n, s.rng("frogs"), voices=28, voice=frog, rate=(0.4, 0.9), jitter=0.3,
                   level=(-8, 0), pan=(-1, 1), presence=(0.2, 1.0), every=6.0)

    # The frogs too far to tell apart: a soft murmur of the same band, so the chorus never stops.
    murmur_level = drift(s.rng("murmur"), s.seconds, every=7.0, lo=0.7, hi=1.0)
    murmur = stereo(*[apply(band(pink(s.n, s.rng("murmur-" + side)), 300, 1300), murmur_level) for side in "ab"],
                    width=0.9)

    return mix((air, 0), (murmur, -9), (frogs, -7))


def plop(r, hz=(700, 260), seconds=0.12):
    """Something small dropping into still water between the stems."""
    out = tone(seconds, hz, ((1, 1.0), (2, 0.1)), attack=0.006, release=seconds * 0.7, curve=1.6)
    return overlay(out, noise_burst(r, 0.04, lo=150, hi=1500, attack=0.004, release=0.03), 0, 0.4)


def boom(r):
    """A bittern's boom: a short indrawn gulp, then three deep hollow notes."""
    out = seq(tone(0.18, (220, 260), ((1, 1.0), (2, 0.3)), attack=0.04, release=0.08), silence(0.25))
    for _ in range(3):
        out = seq(out, tone(0.7, (150, 138), ((1, 1.0), (2, 0.35), (3, 0.12)), attack=0.15, release=0.35,
                            breath=0.05, rng=r), silence(r.uniform(0.25, 0.4)))
    return out


def cues(s):
    # Rare and mostly far: each bed's hero every 90 to 240 s, the others every 3 to 15 minutes, so about one
    # event a minute or less. Only the hero is above level -4, and it is soft-edged.
    r = s.rng
    return [
        # Day's hero: a reed warbler's chatter from the reeds, a run of short notes, a trill, another run.
        cue("warbler", space(seq(phrase(r("warbler"), notes=10, hz=(2200, 4200), note=(0.04, 0.08), gap=(0.02, 0.05)),
                                 trill(r("warbler-trill"), count=5, hz=3400, each=0.025, gap=0.02),
                                 phrase(r("warbler-b"), notes=7, hz=(2400, 4400), note=(0.04, 0.07), gap=(0.02, 0.04))),
                             r("warbler-space"), 0.7, 0.22),
            beds=["day"], every=[90, 240], level=-3, spread=0.9),

        # A frog by day, across the water: two slow croaks.
        cue("croak", distant(space(seq(croak(r("croak"), 210, 0.35, 32), silence(0.3), croak(r("croak-b"), 205, 0.45, 30)),
                                   r("croak-space"), 0.5, 0.2), 0.5),
            beds=["day"], every=[180, 480], level=-6, spread=0.8),

        # A moorhen-like cluck from deep in the reeds: a "kurruk" and a softer one.
        cue("moorhen", distant(space(seq(tone(0.09, (1100, 900), ((1, 1.0), (2, 0.6), (3, 0.3)), attack=0.008,
                                              release=0.03, tremolo=(45, 0.6)), silence(0.03),
                                         tone(0.12, (950, 800), ((1, 1.0), (2, 0.6), (3, 0.3)), attack=0.008,
                                              release=0.04, tremolo=(45, 0.6)), silence(0.5),
                                         gain(tone(0.1, (1000, 850), ((1, 1.0), (2, 0.5)), attack=0.008, release=0.04), -6)),
                                     r("moorhen-space"), 0.6, 0.25), 0.55),
            beds=["day"], every=[240, 600], level=-7, spread=0.9),

        # Something small drops into the water between the stems; by day and by night.
        cue("plop", distant(space(plop(r("plop")), r("plop-space"), 0.5, 0.25), 0.5),
            beds=["day", "night"], every=[240, 720], level=-7, spread=0.7),

        # A dragonfly passing some way off: the soft rattle of its wings rising and falling. Its pulses' peaks are
    # bent by the cue limiter, so the file measures about 5 dB under the cue target: -5 here plays it about as
    # far as the other -8 to -9 cues.
        cue("dragonfly", distant(tone(1.6, [(0, 34), (0.5, 32), (1, 28)], [(k, 1.0 / k) for k in range(1, 14)],
                                      attack=0.7, release=0.8, tremolo=(r("dragonfly").uniform(22, 26), 0.4),
                                      breath=0.2, rng=r("dragonfly-breath")), 0.5),
            beds=["day"], every=[300, 900], level=-5, spread=1.0),

        # Night's hero: a bittern booming somewhere across the fen.
        cue("bittern", distant(space(boom(r("bittern")), r("bittern-space"), 1.2, 0.3, damp=1500), 0.35),
            beds=["night"], every=[90, 240], level=-2, spread=0.9),

        # One frog nearer than the chorus, though still across the water: a run of pulsed croaks.
        cue("frog", distant(space(seq(*[seq(croak(r("frog-%d" % i), 330, 0.25 + 0.04 * i, 34), silence(0.2))
                                        for i in range(4)]), r("frog-space"), 0.5, 0.2), 0.45),
            beds=["night"], every=[180, 480], level=-6, spread=0.7),

        # A heron's croak, far off and harsh: "fraank".
        cue("heron", space(distant(caw(r("heron"), hz=330, seconds=0.45), 0.7), r("heron-space"), 1.0, 0.3),
            beds=["night"], every=[240, 600], level=-8, spread=1.0),

        # A splash in the dark, far off: something larger in the shallows.
        cue("splash", distant(space(seq(noise_burst(r("splash"), 0.35, lo=180, hi=2200, attack=0.02, release=0.28,
                                                    curve=1.8),
                                        plop(r("splash-drop"), (1000, 550), 0.05)), r("splash-space"), 0.6, 0.25), 0.65),
            beds=["night"], every=[300, 900], level=-8, spread=0.8),
    ]
