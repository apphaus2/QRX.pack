"""Marsh: reedbeds, fens and flooded grass.

Day is a reedbed in a light wind: the stems' dry papery rustle, their soft clatter as they touch, a slow trickle of
small bubbles between them, and a busy hum of insects over it all. Night is still water and a frog chorus: many
small voices calling on their own rhythms, near and far, none of them standing out. Every single call, splash or
pass is a cue.

Unlike the forest's leaves (short bright puffs up to 11 kHz), reeds are longer, drier grains held in the middle
band, and they knock: the clatter is thousands of tiny hollow ticks, too small and too many to pick out one.
"""
from lib import *


def day(s):
    # The wind over the reeds: a shallow wandering with small gusts, as in the forest, and a floor.
    calm = drift(s.rng("wind"), s.seconds, every=5.0, lo=0.0, hi=0.6)
    g = gusts(s.rng("gusts"), s.seconds, count=7, rise=(2.5, 4.5), fall=(4.0, 7.0), size=(0.08, 0.16))
    wind = [0.5 + 0.5 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.5))]
    soft = [0.35 + 0.65 * w for w in smooth(wind, 2.0)]

    # A low body of moving air, quieter than the forest's: a marsh is open and low.
    body = stereo(*[apply(moving_lowpass(pink(s.n, s.rng("body-" + side)), scale(wind, 300, 700)), wind)
                    for side in "ab"], width=0.7)

    # The reeds' rustle: longer, papery grains in the middle band, more of them in the gusts but never stopping.
    swish = lambda r: noise_burst(r, r.uniform(0.02, 0.07), lo=r.uniform(1200, 1800), hi=r.uniform(4000, 6000),
                                  attack=0.01, release=0.03)
    rustle = scatter(s.n, s.rng("rustle"), 3500, swish, level=(-10, 0), pan=(-1, 1), follow=soft, depth=1.0)

    # The clatter: stems touching, tiny dry hollow knocks, each a few ms.
    tick = lambda r: knock(r, hz=r.uniform(1400, 2800), seconds=r.uniform(0.015, 0.03), q=4.0, body=0.05)
    clatter = scatter(s.n, s.rng("clatter"), 2200, tick, level=(-12, 0), pan=(-1, 1), follow=soft, depth=1.0)

    # The trickle between the stems: small rising bubble notes, close together and quiet, low in the middle.
    def bubble(r):
        f = r.uniform(700, 1900)
        return tone(r.uniform(0.012, 0.035), (f, f * r.uniform(1.3, 1.8)), attack=0.002, release=0.008)
    trickle_level = drift(s.rng("trickle"), s.seconds, every=6.0, lo=0.6, hi=1.0)
    trickle = scatter(s.n, s.rng("trickle-grains"), 2400, bubble, level=(-12, 0), pan=(-0.5, 0.5),
                      follow=trickle_level, depth=0.6)

    # The insects: many small buzzing fliers, each a long hum at its own wingbeat pitch with a waver, coming and
    # going. Each caller has three buzzes made once, so the chorus costs little.
    def fly(r):
        hz = r.uniform(360, 720)
        buzzes = []
        for _ in range(3):
            t = r.uniform(0.8, 2.4)
            buzzes.append(distant(tone(t, (hz * r.uniform(0.97, 1.03), hz * r.uniform(0.94, 1.06)),
                                       ((1, 1.0), (2, 0.6), (3, 0.35), (4, 0.2), (5, 0.1)),
                                       attack=t * 0.3, release=t * 0.4, vibrato=(r.uniform(3, 7), 0.02),
                                       tremolo=(r.uniform(4, 9), 0.25)), r.uniform(0.3, 0.8)))
        return lambda r2: gain(buzzes[r2.randrange(3)], r2.uniform(-3, 0))
    insects = chorus(s.n, s.rng("insects"), voices=32, voice=fly, rate=(0.3, 0.7), jitter=0.3,
                     level=(-8, 0), pan=(-0.9, 0.9), presence=(0.25, 1.0), every=5.0)

    return mix((body, -3), (rustle, -2), (clatter, -10), (trickle, -12), (insects, -8))


def night(s):
    # Still air over still water: a faint dark hush, barely moving.
    calm = drift(s.rng("calm"), s.seconds, every=7.0, lo=0.75, hi=1.0)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=80), scale(calm, 150, 300)), calm)
                   for side in "ab"], width=0.6)

    # The frogs. Two kinds of caller: small high peepers with a quick pulse, most of them far off, and middling
    # croakers. Each caller keeps its own pitch and pulse, with three calls made once that it chooses among, and
    # the chorus fades each in and out on its own. No deep frogs in the chorus: the few there were stood out
    # alone in the band under 250 Hz; the low voices are cues (the bittern, the nearer frog).
    def frog(r):
        if r.random() < 0.5:
            hz, pulse, length, far = r.uniform(1100, 1900), r.uniform(60, 90), (0.15, 0.35), r.uniform(0.6, 0.9)
        else:
            hz, pulse, length, far = r.uniform(380, 700), r.uniform(25, 40), (0.2, 0.45), r.uniform(0.35, 0.85)
        calls = [distant(croak(r, hz * r.uniform(0.97, 1.03), r.uniform(*length), pulse), far) for _ in range(3)]
        return lambda r2: gain(calls[r2.randrange(3)], r2.uniform(-3, 0))
    frogs = chorus(s.n, s.rng("frogs"), voices=60, voice=frog, rate=(0.6, 1.5), jitter=0.25,
                   level=(-9, 0), pan=(-1, 1), presence=(0.15, 1.0), every=5.0)

    # The frogs too far to tell apart: a soft pulsing murmur of the same bands.
    murmur_level = drift(s.rng("murmur"), s.seconds, every=6.0, lo=0.6, hi=1.0)
    murmur = stereo(*[apply(band(pink(s.n, s.rng("murmur-" + side)), 400, 3200), murmur_level) for side in "ab"],
                    width=0.9)

    return mix((air, -4), (frogs, -2), (murmur, -13))


def plop(r, hz=(800, 280), seconds=0.1):
    """Something small dropping into still water between the stems."""
    out = tone(seconds, hz, ((1, 1.0), (2, 0.1)), attack=0.002, release=seconds * 0.7, curve=2.0)
    return overlay(out, noise_burst(r, 0.03, lo=200, hi=2200, attack=0.001, release=0.025), 0, 0.5)


def boom(r):
    """A bittern's boom: a short indrawn gulp, then three deep hollow notes."""
    out = seq(tone(0.18, (220, 260), ((1, 1.0), (2, 0.3)), attack=0.03, release=0.08), silence(0.25))
    for i in range(3):
        out = seq(out, tone(0.7, (150, 138), ((1, 1.0), (2, 0.35), (3, 0.12)), attack=0.12, release=0.35,
                            breath=0.05, rng=r), silence(r.uniform(0.25, 0.4)))
    return out


def cues(s):
    r = s.rng
    return [
        # A frog by day, close: two slow croaks.
        cue("croak", space(seq(croak(r("croak"), 210, 0.35, 32), silence(0.3), croak(r("croak-b"), 205, 0.45, 30)),
                           r("croak-space"), 0.4, 0.12),
            beds=["day"], every=[25, 70], level=-2, spread=0.8),

        # A moorhen-like cluck from the reeds: a sharp "kurruk" and a softer one.
        cue("moorhen", space(seq(tone(0.09, (1100, 900), ((1, 1.0), (2, 0.6), (3, 0.3)), attack=0.004, release=0.03,
                                      tremolo=(45, 0.6)), silence(0.03),
                                 tone(0.12, (950, 800), ((1, 1.0), (2, 0.6), (3, 0.3)), attack=0.004, release=0.04,
                                      tremolo=(45, 0.6)), silence(0.5),
                                 gain(tone(0.1, (1000, 850), ((1, 1.0), (2, 0.5)), attack=0.004, release=0.04), -6)),
                             r("moorhen-space"), 0.5, 0.18),
            beds=["day"], every=[30, 90], level=-3, spread=0.9),

        # Something small drops into the water; by day and by night.
        cue("plop", space(plop(r("plop")), r("plop-space"), 0.4, 0.15),
            beds=["day", "night"], every=[25, 80], level=-4, spread=0.7),

        # A dragonfly passes: the dry rattle of its wings rising and falling as it goes by, a little Doppler fall.
        cue("dragonfly", tone(1.6, [(0, 34), (0.5, 32), (1, 28)], [(k, 1.0 / k) for k in range(1, 40)],
                              attack=0.7, release=0.8, tremolo=(r("dragonfly").uniform(22, 26), 0.5), breath=0.3,
                              rng=r("dragonfly-breath")),
            beds=["day"], every=[40, 110], level=-2, spread=1.0),

        # A reed warbler's chatter: a long run of short harsh notes, repeated and jumbled.
        cue("warbler", space(seq(phrase(r("warbler"), notes=12, hz=(2200, 4600), note=(0.03, 0.07), gap=(0.01, 0.04)),
                                 trill(r("warbler-trill"), count=6, hz=3600, each=0.02, gap=0.015),
                                 phrase(r("warbler-b"), notes=9, hz=(2400, 5000), note=(0.03, 0.06), gap=(0.01, 0.03))),
                             r("warbler-space"), 0.5, 0.15),
            beds=["day"], every=[20, 60], level=-2, spread=0.9),

        # A bittern booming somewhere across the fen.
        cue("bittern", distant(space(boom(r("bittern")), r("bittern-space"), 1.2, 0.3, damp=1500), 0.4),
            beds=["night"], every=[45, 120], level=-3, spread=0.9),

        # A splash in the dark: something larger in the shallows.
        cue("splash", space(seq(noise_burst(r("splash"), 0.3, lo=200, hi=3500, attack=0.005, release=0.25, curve=2.0),
                                plop(r("splash-drop"), (1200, 600), 0.04), silence(0.1), plop(r("splash-drop2"), (1400, 700), 0.03)),
                            r("splash-space"), 0.5, 0.15),
            beds=["night"], every=[40, 110], level=-3, spread=0.8),

        # One frog much nearer than the chorus: a run of deep pulsed croaks.
        cue("frog-near", space(seq(*[seq(croak(r("frog-near"), 330, r("frog-len").uniform(0.25, 0.4), 34), silence(0.18))
                                     for _ in range(4)]), r("frog-near-space"), 0.4, 0.12),
            beds=["night"], every=[30, 80], level=-1, spread=0.7),

        # A heron's croak, far off and harsh: "fraank".
        cue("heron", space(distant(caw(r("heron"), hz=330, seconds=0.45), 0.6), r("heron-space"), 1.0, 0.3),
            beds=["night"], every=[50, 140], level=-6, spread=1.0),
    ]
