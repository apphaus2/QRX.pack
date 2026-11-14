"""Barrens: desert, dunes, rock and scree.

A soft backdrop, not a portrait. Day is a low, dry breath of wind over open ground: less of the forest's dark body
and more of a broad, soft middle (open air with nothing to roar in), over the faintest dull grain of sand moving,
swelling and settling slowly. Night is near silence: a low, cold breath and, very faint, a scatter of dry ticks
(insects far off). Everything you could pick out as one thing is a cue, and cues are rare and mostly far; each bed
has one soft hero (a hawk's cry by day, an owl by night).
"""
from lib import *

# The night is near silence: suggested a little under the day.
LEVEL = {"day": 0.0, "night": -3.0}


def day(s):
    # The wind: slow wandering with small gusts over a high floor, about 4 dB from lull to swell (see forest.py).
    calm = drift(s.rng("wind"), s.seconds, every=6.5, lo=0.0, hi=0.45)
    g = gusts(s.rng("gusts"), s.seconds, count=6, rise=(3.0, 5.5), fall=(4.5, 8.0), size=(0.06, 0.14))
    wind = [0.6 + 0.4 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.5))]

    # A little dark body under it, quieter than the forest's: open ground has nothing to roar in.
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("body-" + side), corner=90), scale(wind, 140, 320)), wind)
                    for side in "ab"], width=0.7)

    # The broad, dry rush: pink noise from 180 Hz to a cutoff that opens from 450 to 1300 Hz with the wind. This
    # is most of the bed and what makes it the desert's: a wide soft middle rather than a dark roar.
    rush = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("rush-" + side)), scale(wind, 450, 1300)), 180),
                          wind) for side in "ab"], width=0.85)

    # Sand: a faint, dull grain, tiny puffs (3 to 10 ms) from 900 Hz to under 3 kHz, finer than the forest's
    # leaves and never bright; a little thicker in a gust and never stopping.
    grain = lambda r: noise_burst(r, r.uniform(0.003, 0.01), lo=900, hi=r.uniform(2000, 3000), attack=0.001,
                                  release=0.004)
    sand = scatter(s.n, s.rng("sand"), 6000, grain, level=(-10, 0), pan=(-1, 1),
                   follow=[0.5 + 0.5 * w for w in smooth(wind, 2.0)], depth=1.0)

    return mix((body, -4), (rush, 0), (sand, -13))


def night(s):
    # The cold breath: dark, slow air, narrow in its movement.
    calm = drift(s.rng("calm"), s.seconds, every=7.0, lo=0.55, hi=0.85)
    breath = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("breath-" + side), corner=60), scale(calm, 110, 280)),
                            calm) for side in "ab"], width=0.6)

    # Insects far off: single dry ticks at 2.4 to 3.6 kHz (not the forest's pulsed 4 to 5 kHz chirps), each
    # caller slow and dulled by distance, so together they are a faint stipple on the silence.
    def ticker(r):
        hz = r.uniform(2400, 3600)
        call = distant(chirp(r.uniform(0.006, 0.01), hz * 1.03, hz * 0.97), r.uniform(0.5, 0.85))
        return lambda r2: gain(call, r2.uniform(-4, 0))
    ticks = chorus(s.n, s.rng("ticks"), voices=18, voice=ticker, rate=(0.8, 2.2), jitter=0.3,
                   level=(-12, 0), pan=(-0.9, 0.9), presence=(0.1, 1.0), every=6.0)

    return mix((breath, 0), (ticks, -9))


def rockfall(r):
    """A small slide of scree, soft-edged: a dozen low knocks (no thump: the codec drops it) over a dusty hiss."""
    out = [v * 0.3 for v in noise_burst(r, 1.3, lo=200, hi=2000, attack=0.1, release=0.7, curve=1.5)]
    for _ in range(r.randint(10, 14)):
        overlay(out, knock(r, r.uniform(500, 1600), 0.08, q=4.0, body=0.0), r.uniform(0.05, 1.0) ** 1.3,
                r.uniform(0.3, 1.0))
    return out


def rattle(r):
    """Dry grass stems knocking in a puff of wind: a thin crackle that rises and falls."""
    seconds = r.uniform(0.8, 1.1)
    out = silence(seconds)
    t = 0.0
    while t < seconds - 0.01:
        u = t / seconds
        g = (1 - abs(2 * u - 1)) ** 1.2 * r.uniform(0.4, 1.0)
        overlay(out, noise_burst(r, r.uniform(0.004, 0.01), lo=1500, hi=5000, attack=0.001, release=0.004), t, g)
        t += r.uniform(0.01, 0.03)
    return out


def scuttle(r):
    """A lizard running over grit: two short runs of soft scratches with a pause between."""
    out, t = silence(0.05), 0.0
    for _ in range(2):
        for _ in range(r.randint(7, 11)):
            overlay(out, noise_burst(r, r.uniform(0.008, 0.016), lo=1200, hi=4500, attack=0.002, release=0.006),
                    t, r.uniform(0.5, 1.0))
            t += r.uniform(0.028, 0.05)
        t += r.uniform(0.25, 0.45)
    return [v * e for v, e in zip(out, envelope(len(out) / RATE, attack=0.04, release=0.06))]


def gecko(r):
    """A gecko's chirps: six or seven raspy "tchk"s, slowing and fading, with soft attacks."""
    parts, gap, g = [], 0.12, 1.0
    for _ in range(r.randint(6, 7)):
        hz = r.uniform(1900, 2300)
        note = tone(0.06, (hz, hz * 0.8), ((1, 1.0), (2, 0.3)), attack=0.012, release=0.03,
                    tremolo=(r.uniform(110, 140), 0.5))
        parts += [gain(note, db(g)), silence(gap)]
        gap *= r.uniform(1.12, 1.22)
        g *= 0.85
    return seq(*parts[:-1])


def cues(s):
    # Rare and mostly far (README, "Cues are rare, and mostly far"): each bed's hero every 90 to 240 s, the rest
    # every 3 to 15 minutes, about one event a minute or less. Only the heroes are above level -4.
    r = s.rng
    return [
        # Day's hero: a hawk high up, one long falling "kee-ah", in the open air.
        cue("hawk", space(distant(tone(1.0, [(0.0, 2300), (0.15, 2700), (1.0, 1900)], ((1, 1.0), (2, 0.2)),
                                       attack=0.08, release=0.4, vibrato=(9.0, 0.01), breath=0.04, rng=r("hawk")),
                                  0.4), r("hawk-space"), 1.4, 0.3),
            beds=["day"], every=[90, 240], level=-3, spread=1.0),

        # A raven far off: two deep, rough croaks.
        cue("raven", space(distant(seq(caw(r("raven-a"), 330, 0.32), silence(0.45), caw(r("raven-b"), 310, 0.38)),
                                   0.7), r("raven-space"), 1.2, 0.3),
            beds=["day"], every=[180, 480], level=-6, spread=1.0),

        # A small rockfall on a far slope: low-passed by distance and rare.
        cue("rockfall", space(distant(rockfall(r("rockfall")), 0.8), r("rockfall-space"), 1.2, 0.35),
            beds=["day"], every=[300, 900], level=-8, spread=1.0),

        # Dry grass rattling in a puff of wind, a little way off.
        cue("rattle", distant(space(rattle(r("rattle")), r("rattle-space"), 0.5, 0.2), 0.6),
            beds=["day"], every=[180, 600], level=-8, spread=0.9),

        # A lizard scuttling over the grit some way off; by day and by night.
        cue("scuttle", distant(space(scuttle(r("scuttle")), r("scuttle-space"), 0.4, 0.2), 0.6),
            beds=["day", "night"], every=[240, 600], level=-8, spread=0.8),

        # Night's hero: an owl far off, two short deep hoots, lower and plainer than the forest's.
        cue("owl", space(distant(seq(hoot(300, 0.34, 0.95, rng=r("owl-a")), silence(0.3),
                                     hoot(290, 0.45, 0.9, rng=r("owl-b"))), 0.45), r("owl-space"), 1.4, 0.3),
            beds=["night"], every=[90, 240], level=-2, spread=1.0),

        # A gecko chirping from the rocks, a little way off.
        cue("gecko", distant(space(gecko(r("gecko")), r("gecko-space"), 0.5, 0.2), 0.55),
            beds=["night"], every=[240, 600], level=-7, spread=0.8),

        # A rock ticking as it cools, far off: sharp by nature, so far, quiet and rare.
        cue("tick", distant(space(seq(knock(r("tick-a"), 2600, 0.05, q=10.0, body=0.0), silence(0.35),
                                      gain(knock(r("tick-b"), 2400, 0.05, q=10.0, body=0.0), -8)),
                                  r("tick-space"), 0.6, 0.3), 0.7),
            beds=["night"], every=[300, 900], level=-9, spread=0.9),

        # Something howling very far away: one soft tone that rises, holds and falls.
        cue("howl", space(distant(tone(2.6, [(0.0, 520), (0.3, 760), (0.7, 700), (1.0, 560)],
                                       ((1, 1.0), (2, 0.3), (3, 0.08)), attack=0.3, release=0.9,
                                       vibrato=(5.5, 0.012), breath=0.03, rng=r("howl")), 0.75),
                          r("howl-space"), 1.2, 0.4),
            beds=["night"], every=[240, 600], level=-7, spread=1.0),
    ]
