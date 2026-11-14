"""Barrens: desert, dunes, rock and scree.

Day is a broad, dry wind over open ground: a wide middle-band rush with little low body (no trees to roar in),
and sand hissing along the surface, a fine high grit that thickens in the gusts and thins, but never stops, in
the hot stillness between them. Night is near silence: a low, cold breath of air and, very faint and high, a
ticking shimmer of insects. Every distinct thing (a pebble, a raven, a gecko) is a cue.
"""
from lib import *

# The night is near silence: suggested a little under the day.
LEVEL = {"day": 0.0, "night": -3.0}


def day(s):
    # The wind: slow wandering with a few soft gusts, and a high floor, so the stillness between gusts is quieter
    # air, not a hole. Shallow on purpose (see forest.py): `stand` fires on deep or quick swells.
    calm = drift(s.rng("wind"), s.seconds, every=5.5, lo=0.0, hi=0.6)
    g = gusts(s.rng("gusts"), s.seconds, count=7, rise=(2.5, 5.0), fall=(4.0, 8.0), size=(0.08, 0.2))
    wind = [0.45 + 0.55 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.5))]

    # The rush: pink noise kept broad (150 Hz up to a cutoff that opens with the wind, 900 to 2200 Hz). Dry
    # air over open ground has little of the forest's low roar, so the body is mostly this middle band.
    rush = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("rush-" + side)), scale(wind, 900, 2200)), 150),
                          wind) for side in "ab"], width=0.85)

    # A little ground under it: a faint dark rumble so the wind is not all hiss.
    ground = stereo(*[lowpass(brown(s.n, s.rng("ground-" + side), corner=80), 220) for side in "ab"], width=0.5)

    # The sand: a continuous fine hiss (blue noise, 3 to 9 kHz) that rises more steeply than the rush in a
    # gust, with a floor so it never falls silent.
    sand_level = [0.35 + 0.65 * w ** 1.5 for w in smooth(wind, 2.0)]
    sand = stereo(*[apply(lowpass(highpass(blue(s.n, s.rng("sand-" + side)), 3000), 9000), sand_level)
                    for side in "ab"], width=0.9)

    # The grit: many tiny, very short grains (2 to 6 ms, finer than the forest's leaves), the texture of sand
    # skating over sand. More of them in the gusts.
    grain = lambda r: noise_burst(r, r.uniform(0.002, 0.006), lo=r.uniform(3500, 5000), hi=r.uniform(8000, 12000),
                                  attack=0.0005, release=0.002)
    grit = scatter(s.n, s.rng("grit"), 9000, grain, level=(-14, 0), pan=(-1, 1),
                   follow=[0.3 + 0.7 * w for w in smooth(wind, 2.0)], depth=1.0)

    return mix((rush, 0), (ground, -13), (sand, -7), (grit, -9))


def night(s):
    # The cold breath: dark, slow air, low and narrow in its movement.
    calm = drift(s.rng("calm"), s.seconds, every=7.0, lo=0.5, hi=0.85)
    breath = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("breath-" + side), corner=60), scale(calm, 110, 300)),
                            calm) for side in "ab"], width=0.6)

    # The insects: tiny single ticks high up (7 to 9.5 kHz, well above the forest's crickets), each caller on
    # its own quick rate and far off, so together they are a faint dry stipple, not a song.
    def ticker(r):
        hz = r.uniform(7000, 9500)
        length = r.uniform(0.004, 0.008)
        call = distant(chirp(length, hz * 1.03, hz * 0.97), r.uniform(0.0, 0.3))
        return lambda r2: gain(call, r2.uniform(-4, 0))
    ticks = chorus(s.n, s.rng("ticks"), voices=24, voice=ticker, rate=(3.0, 7.0), jitter=0.25,
                   level=(-12, 0), pan=(-0.95, 0.95), presence=(0.1, 1.0), every=6.0)

    # And under them the faintest high shimmer, wandering on its own.
    shimmer_level = drift(s.rng("shimmer"), s.seconds, every=8.0, lo=0.5, hi=1.0)
    shimmer = stereo(*[apply(band(white(s.n, s.rng("shimmer-" + side)), 7000, 10000), shimmer_level)
                       for side in "ab"], width=0.9)

    return mix((breath, 0), (ticks, -6), (shimmer, -15))


def skitter(r):
    """A pebble knocked loose: bright little knocks bouncing further apart and softer, then a couple of grains."""
    out, t, gap, g = silence(0.05), 0.0, r.uniform(0.05, 0.08), 1.0
    for _ in range(r.randint(5, 7)):
        overlay(out, knock(r, r.uniform(2200, 3800), 0.04, q=6.0, body=0.0), t, g)
        t += gap
        gap *= r.uniform(0.75, 0.9)        # a bounce: each one comes sooner
        g *= r.uniform(0.6, 0.8)
    return out


def rockfall(r):
    """A small slide of scree: a dozen knocks of different sizes over a second, over a dusty hiss."""
    out = noise_burst(r, 1.3, lo=250, hi=3000, attack=0.08, release=0.7, curve=1.5)
    out = [v * 0.25 for v in out]
    for _ in range(r.randint(12, 16)):
        hz = r.uniform(700, 3200)
        overlay(out, knock(r, hz, 0.07, q=5.0, body=0.6), r.uniform(0.0, 1.0) ** 1.4, r.uniform(0.3, 1.0))
    return out


def rattle(r):
    """Dry grass stems knocking in a puff of wind: a quick, thin crackle that rises and falls."""
    seconds = r.uniform(0.7, 1.0)
    out = silence(seconds)
    t = 0.0
    while t < seconds - 0.01:
        u = t / seconds
        g = (1 - abs(2 * u - 1)) ** 1.2 * r.uniform(0.4, 1.0)
        overlay(out, noise_burst(r, r.uniform(0.003, 0.008), lo=2500, hi=7500, attack=0.0005, release=0.003), t, g)
        t += r.uniform(0.008, 0.025)
    return out


def scuttle(r):
    """A lizard running over grit: two short runs of soft scratches with a pause between."""
    out, t = silence(0.05), 0.0
    for run in range(2):
        for _ in range(r.randint(7, 11)):
            overlay(out, noise_burst(r, r.uniform(0.008, 0.016), lo=1500, hi=6000, attack=0.001, release=0.006),
                    t, r.uniform(0.5, 1.0))
            t += r.uniform(0.028, 0.05)
        t += r.uniform(0.25, 0.45)
    # a soft start and end, so the first scratch is not a click at the very edge
    return [v * e for v, e in zip(out, envelope(len(out) / RATE, attack=0.04, release=0.06))]


def gecko(r):
    """A gecko's chirps: six or seven raspy "tchk"s, slowing and fading."""
    parts, gap, g = [], 0.11, 1.0
    for _ in range(r.randint(6, 7)):
        hz = r.uniform(2100, 2500)
        note = tone(0.05, (hz, hz * 0.78), ((1, 1.0), (2, 0.35), (3, 0.15)), attack=0.004, release=0.02,
                    tremolo=(r.uniform(110, 140), 0.6))
        parts += [gain(note, db(g)), silence(gap)]
        gap *= r.uniform(1.12, 1.22)
        g *= 0.85
    return seq(*parts[:-1])


def cues(s):
    r = s.rng
    return [
        # A pebble skittering down a slope nearby; by day and by night.
        cue("skitter", space(skitter(r("skitter")), r("skitter-space"), 0.5, 0.15),
            beds=["day", "night"], every=[30, 90], level=-3, spread=0.8),

        # A small rockfall on a far slope: dull with distance, in the open.
        cue("rockfall", space(distant(rockfall(r("rockfall")), 0.55), r("rockfall-space"), 1.2, 0.3),
            beds=["day"], every=[70, 180], level=-5, spread=1.0),

        # A raven, far off: two deep, rough croaks.
        cue("raven", space(distant(seq(caw(r("raven-a"), 330, 0.32), silence(0.45), caw(r("raven-b"), 310, 0.38)), 0.5),
                           r("raven-space"), 1.2, 0.3),
            beds=["day"], every=[40, 110], level=-5, spread=1.0),

        # Dry grass rattling in a puff of wind.
        cue("rattle", space(rattle(r("rattle")), r("rattle-space"), 0.4, 0.12),
            beds=["day"], every=[18, 45], level=-5, spread=0.9),

        # A lizard scuttling over the grit close by.
        cue("scuttle", space(scuttle(r("scuttle")), r("scuttle-space"), 0.3, 0.1),
            beds=["day", "night"], every=[35, 100], level=-4, spread=0.7),

        # A hawk high up: one long "kee-ah", falling, far away.
        cue("hawk", space(distant(tone(0.9, [(0.0, 2600), (0.15, 3100), (1.0, 2200)], ((1, 1.0), (2, 0.25), (3, 0.08)),
                                       attack=0.04, release=0.35, vibrato=(9.0, 0.01), breath=0.05, rng=r("hawk")), 0.55),
                          r("hawk-space"), 1.4, 0.3),
            beds=["day"], every=[45, 130], level=-6, spread=1.0),

        # A gecko chirping from the rocks.
        cue("gecko", space(gecko(r("gecko")), r("gecko-space"), 0.5, 0.18),
            beds=["night"], every=[20, 60], level=-3, spread=0.8),

        # An owl far off: two short, deep hoots, lower and plainer than the forest's.
        cue("owl", space(distant(seq(hoot(300, 0.32, 0.95, rng=r("owl-a")), silence(0.3), hoot(290, 0.42, 0.9, rng=r("owl-b"))),
                                 0.6), r("owl-space"), 1.4, 0.3),
            beds=["night"], every=[40, 110], level=-5, spread=1.0),

        # A rock ticking as it cools: one small hard click and a fainter one after it.
        cue("tick", space(seq(knock(r("tick-a"), 3600, 0.05, q=12.0, body=0.0), silence(0.35),
                              gain(knock(r("tick-b"), 3300, 0.05, q=12.0, body=0.0), -8)), r("tick-space"), 0.5, 0.15),
            beds=["night"], every=[25, 80], level=-5, spread=0.9),

        # Something howling very far away: one soft tone that rises, holds and falls.
        cue("howl", space(distant(tone(2.6, [(0.0, 520), (0.3, 760), (0.7, 700), (1.0, 560)],
                                       ((1, 1.0), (2, 0.3), (3, 0.08)), attack=0.3, release=0.9,
                                       vibrato=(5.5, 0.012), breath=0.03, rng=r("howl")), 0.75),
                          r("howl-space"), 1.2, 0.4),
            beds=["night"], every=[60, 180], level=-7, spread=1.0),
    ]
