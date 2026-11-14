"""Forest: woods and plantations, bark, leaf litter and the dark under the canopy.

A soft backdrop, not a portrait: day is a low breath of wind in the canopy, a dark body of moving air with the
crowns' rush just above it and a faint, dull rustle of leaves, swelling and settling slowly. Night is stiller air
and a soft chorus of crickets. Anything you could pick out as one thing (a bird, a knock, a creak) is a cue, and
cues are rare: about one a minute or less, most of them far off. Each bed has one hero, the sound that says
"forest" (a songbird by day, an owl by night), allowed a little nearer.

This file is the reference recipe: copy it to recipes/<biome>.py and change the sounds. The build calls `day(s)`
and `night(s)` in loop mode and `cues(s)` in one-shot mode; see README.md, "Writing a recipe".
"""
from lib import *


def day(s):
    # The wind's shape, which every layer follows: a slow random wandering (a new level about every 6 s) with
    # small gusts on top, over a floor so the stillness is quiet, never silent. Kept shallow on purpose (about
    # 4 dB from lull to swell): a deep or quick swell, or a long lull, is a landmark heard every 30 s, and the
    # owner found the first, livelier version harsh.
    calm = drift(s.rng("wind"), s.seconds, every=6.0, lo=0.0, hi=0.45)
    g = gusts(s.rng("gusts"), s.seconds, count=8, rise=(3.0, 5.0), fall=(4.0, 8.0), size=(0.06, 0.14))
    wind = [0.6 + 0.4 * min(1.0, a + b) for a, b in zip(calm, smooth(g, 1.5))]

    # The body: dark moving air, a little louder and brighter as the wind rises. Two unrelated noises, one as
    # the middle and one as the sides, are what make it wide (stereo()).
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("body-" + side), corner=90), scale(wind, 140, 360)), wind)
                    for side in "ab"], width=0.7)

    # The crowns: pink noise, kept under about 1.8 kHz. This is most of what a listener hears, so it is what
    # sets the bed's brightness: the first version opened it to 3.2 kHz and the day was harsh.
    crown = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("crown-" + side)), scale(wind, 600, 1800)), 200),
                           wind) for side in "ab"], width=0.8)

    # The leaves: a faint, dull rustle (small puffs of noise from 1.5 to about 5 kHz, never the bright hiss
    # above that), a little thicker where the wind is up, and never stopping.
    leaf = lambda r: noise_burst(r, r.uniform(0.008, 0.03), lo=1500, hi=r.uniform(3500, 5500), attack=0.003,
                                 release=0.012)
    leaves = scatter(s.n, s.rng("leaves"), 3000, leaf, level=(-8, 0), pan=(-1, 1),
                     follow=[0.4 + 0.6 * w for w in smooth(wind, 2.0)], depth=1.0)

    return mix((body, 0), (crown, -1), (leaves, -10))


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
        call = distant(call, r.uniform(0.3, 0.8))          # all a little way off; none at the listener's feet
        return lambda r2: gain(call, r2.uniform(-2, 0))    # each chirp a little different in level
    crickets = chorus(s.n, s.rng("crickets"), voices=20, voice=cricket, rate=(1.3, 2.6), jitter=0.06,
                      level=(-10, 0), pan=(-0.9, 0.9), presence=(0.15, 1.0), every=5.0)

    # Far off, the many crickets too distant to tell apart merge into a faint shimmer.
    shimmer_level = drift(s.rng("shimmer"), s.seconds, every=7.0, lo=0.5, hi=1.0)
    shimmer = stereo(*[apply(band(white(s.n, s.rng("shimmer-" + side)), 3800, 5600), shimmer_level)
                       for side in "ab"], width=0.9)

    # The air is most of the energy; the crickets sit on it, softly.
    return mix((air, 0), (crickets, -7), (shimmer, -20))


def crow(r):
    """Three caws, each a little different, with a pause after each."""
    return seq(*[seq(caw(r, r.uniform(560, 640), r.uniform(0.26, 0.34)), silence(r.uniform(0.25, 0.4)))
                 for _ in range(3)])


def cues(s):
    # Rare and mostly far: the commonest cue of a bed (its hero) comes every 90 to 240 s, the others every 3 to
    # 10 minutes, so a listener hears about one event a minute or less and sometimes minutes of nothing.
    # Levels: every cue file's loudest 100 ms is 6 dB over a nominal bed's RMS, so level 0 would be a near,
    # clear call; the hero sits at -2, everything else at -6 to -9 and `distant`. Nothing sharp is near.
    r = s.rng      # r("name") is a new fixed source each call; a cue that draws in a loop keeps one
    return [
        # Day's hero: a songbird's free phrase, seven whistled notes, in the open air.
        cue("song-warble", space(phrase(r("warble"), notes=7, hz=(2800, 5200)), r("warble-space"), 0.8, 0.22),
            beds=["day"], every=[90, 240], level=-2, spread=0.9),

        # Another bird further off, a two-note "tee-too" said three times.
        cue("song-teetoo", distant(space(phrase(r("teetoo"), shape=[(5200, 5000, 0.09), (3700, 3450, 0.13)] * 3,
                                                gap=(0.05, 0.09)), r("teetoo-space"), 0.7, 0.22), 0.45),
            beds=["day"], every=[180, 420], level=-6, spread=0.9),

        # A woodpecker drumming, well away: a roll of knocks on hollow wood, dulled by distance.
        cue("woodpecker", distant(space(roll(r("woodpecker"), count=16, rate=17, hz=1050, accel=0.25, fade=0.55),
                                        r("woodpecker-space"), 0.8, 0.3), 0.65),
            beds=["day"], every=[240, 600], level=-7, spread=0.8),

        # A crow, far away: three caws, dull with distance, in the open air.
        cue("crow", space(distant(crow(r("crow")), 0.7), r("crow-space"), 1.0, 0.3),
            beds=["day"], every=[240, 600], level=-8, spread=1.0),

        # Night's hero: an owl, "hoo ... hu-hoooo", the last note long and wavering.
        cue("owl", distant(space(seq(hoot(410, 0.5, rng=r("owl-a")), silence(0.9), hoot(420, 0.16, 0.97),
                                     silence(0.1), hoot(405, 1.05, 0.86, rng=r("owl-b"))), r("owl-space"), 0.8, 0.25),
                           0.4),
            beds=["night"], every=[90, 240], level=-2, spread=0.8),

        # A nightjar's churr far off: a long dry trill that shifts its pitch twice.
        cue("churr", space(distant(churr(r("churr"), 3.0, hz=1000, pulse=(26, 30)), 0.6), r("churr-space"), 0.5, 0.2),
            beds=["night"], every=[180, 480], level=-8, spread=0.8),

        # A branch creaking somewhere in the dark as the trees move.
        cue("creak", distant(space(creak(r("creak"), 1.4), r("creak-space"), 0.6, 0.25), 0.5),
            beds=["night"], every=[240, 600], level=-7, spread=0.7),

        # A twig breaking a long way off: something moving in the night. Sharp, so far and rare.
        cue("twig", distant(space(snap(r("twig")), r("twig-space"), 0.5, 0.3), 0.7),
            beds=["night"], every=[300, 900], level=-9, spread=0.7),
    ]
