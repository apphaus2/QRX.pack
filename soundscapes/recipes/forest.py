"""Forest: woods and plantations, bark, leaf litter and the dark under the canopy.

Day is wind in the canopy: a dark body of moving air, the rush of the crowns above it, and the leaves, a brighter
patter that comes and goes with the wind, with quieter stretches between. Night is stiller air and a
soft chorus of crickets. Everything you could pick out as one thing (a bird, a knock, a snap) is a cue.

This file is the reference recipe: copy it to recipes/<biome>.py and change the sounds. The build calls `day(s)`
and `night(s)` in loop mode and `cues(s)` in one-shot mode; see README.md, "Writing a recipe".
"""
from lib import *


def day(s):
    # The wind's shape, which every layer follows: a slow random wandering (a new level about every 5 s) with
    # small gusts on top, and a floor so stillness is quiet, not silent. Kept shallow (about 5 dB) on purpose:
    # deeper or quicker swells, or many big gusts summed into one long lull, made the check's `stand` fire, and
    # a swell or a lull that comes round every 30 s is a landmark as much as a bird is.
    calm = drift(s.rng("wind"), s.seconds, every=5.0, lo=0.0, hi=0.6)
    g = gusts(s.rng("gusts"), s.seconds, count=8, rise=(2.5, 4.5), fall=(4.0, 7.0), size=(0.08, 0.18))
    wind = [0.45 + 0.55 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.5))]

    # The body: dark moving air, louder and a little brighter as the wind rises. Two unrelated noises, one as
    # the middle and one as the sides, are what make it wide (stereo()).
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("body-" + side), corner=90), scale(wind, 140, 420)), wind)
                    for side in "ab"], width=0.7)

    # The crowns: pink noise in the middle band. Its cutoff and its level both follow the wind, a little more
    # steeply than the body (wind ** 1.3), so a gust is heard mostly up here.
    crown = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("crown-" + side)), scale(wind, 700, 2400)), 250),
                           [w ** 1.3 for w in wind]) for side in "ab"], width=0.8)

    # The leaves: thousands of tiny bright puffs of noise, more of them and louder where the wind is high. Short
    # grains at random places across the stereo field read as rustle, not as events. They follow a softened
    # copy of the wind and never stop: leaves that fall silent the moment a gust ends make that moment a
    # landmark (the check's `stand` caught it in the 8 kHz band).
    leaf = lambda r: noise_burst(r, r.uniform(0.006, 0.03), lo=2500, hi=r.uniform(6000, 11000), attack=0.002,
                                 release=0.01)
    leaves = scatter(s.n, s.rng("leaves"), 4000, leaf, level=(-10, 0), pan=(-1, 1),
                     follow=[0.3 + 0.7 * w for w in smooth(wind, 2.0)], depth=1.0)

    return mix((body, -2), (crown, 0), (leaves, -6))


def night(s):
    # Stiller air: the same kind of body, slower and narrower in its movement.
    calm = drift(s.rng("calm"), s.seconds, every=6.0, lo=0.55, hi=0.85)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=70), scale(calm, 120, 260)), calm)
                   for side in "ab"], width=0.6)

    # The crickets. Each caller has its own pitch and distance, and calls a three- or four-pulse chirp over and
    # over at its own rate; `chorus` fades each in and out on its own, so the mix keeps thinning and filling.
    def cricket(r):
        hz = r.uniform(4200, 5200)
        pulses, length, gap = r.randint(3, 4), r.uniform(0.010, 0.014), r.uniform(0.016, 0.022)
        call = seq(*[seq(chirp(length, hz * 1.01, hz * 0.99), silence(gap)) for _ in range(pulses)])
        call = distant(call, r.uniform(0.1, 0.7))          # some near, most further off
        return lambda r2: gain(call, r2.uniform(-2, 0))    # each chirp a little different in level
    crickets = chorus(s.n, s.rng("crickets"), voices=20, voice=cricket, rate=(1.3, 2.6), jitter=0.06,
                      level=(-10, 0), pan=(-0.9, 0.9), presence=(0.15, 1.0), every=5.0)

    # Far off, the many crickets too distant to tell apart merge into a faint shimmer.
    shimmer_level = drift(s.rng("shimmer"), s.seconds, every=7.0, lo=0.5, hi=1.0)
    shimmer = stereo(*[apply(band(white(s.n, s.rng("shimmer-" + side)), 3800, 5600), shimmer_level)
                       for side in "ab"], width=0.9)

    # The air is most of the energy but little of what is heard; the crickets carry the bed.
    return mix((air, 0), (crickets, -5), (shimmer, -18))


def crow(r):
    """Three caws, each a little different, with a pause after each."""
    return seq(*[seq(caw(r, r.uniform(560, 640), r.uniform(0.26, 0.34)), silence(r.uniform(0.25, 0.4)))
                 for _ in range(3)])


def cues(s):
    # Levels: every cue file's loudest 100 ms is 6 dB over the bed's RMS, so `level` 0 is a near, clear call
    # and -6 is level with the bed; the build prints each cue's "over bed" figure.
    r = s.rng      # r("name") is a fixed random source of its own for each sound
    return [
        # A woodpecker drumming: a roll of knocks on hollow wood, speeding up a little and fading, some way off.
        cue("woodpecker", distant(space(roll(r("woodpecker"), count=16, rate=17, hz=1050, accel=0.25, fade=0.55),
                                        r("woodpecker-space"), 0.7, 0.22), 0.3),
            beds=["day"], every=[35, 90], level=-2, spread=0.8),

        # A songbird's free phrase: seven whistled notes, wandering.
        cue("song-warble", space(phrase(r("warble"), notes=7, hz=(2800, 5200)), r("warble-space"), 0.6, 0.18),
            beds=["day"], every=[12, 35], level=0, spread=0.9),

        # Another bird, a two-note "tee-too" said three times.
        cue("song-teetoo", space(phrase(r("teetoo"), shape=[(5200, 5000, 0.09), (3700, 3450, 0.13)] * 3,
                                        gap=(0.05, 0.09)), r("teetoo-space"), 0.6, 0.18),
            beds=["day"], every=[20, 50], level=-1, spread=0.9),

        # A twig breaking underfoot somewhere nearby; by day and by night.
        cue("twig", space(snap(r("twig")), r("twig-space"), 0.4, 0.15),
            beds=["day", "night"], every=[45, 120], level=-1, spread=0.7),

        # A crow, far away: three caws, dull with distance, in the open air.
        cue("crow", space(distant(crow(r("crow")), 0.6), r("crow-space"), 1.0, 0.3),
            beds=["day"], every=[45, 120], level=-6, spread=1.0),

        # An owl: "hoo ... hu-hoooo", the last note long and wavering.
        cue("owl", distant(space(seq(hoot(410, 0.5, rng=r("owl-a")), silence(0.9), hoot(420, 0.16, 0.97),
                                     silence(0.1), hoot(405, 1.05, 0.86, rng=r("owl-b"))), r("owl-space"), 0.8, 0.25),
                           0.35),
            beds=["night"], every=[25, 70], level=-1, spread=0.8),

        # A nightjar's churr: a long dry mechanical trill that shifts its pitch twice.
        cue("churr", space(distant(churr(r("churr"), 3.0, hz=1000, pulse=(26, 30)), 0.5), r("churr-space"), 0.5, 0.2),
            beds=["night"], every=[30, 90], level=-7, spread=0.8),

        # A branch creaking as the trees move.
        cue("creak", space(creak(r("creak"), 1.4), r("creak-space"), 0.6, 0.2),
            beds=["night"], every=[35, 100], level=-2, spread=0.7),
    ]
