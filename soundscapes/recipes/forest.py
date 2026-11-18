"""Forest: woods and plantations, bark, leaf litter and the dark under the canopy.

A soft backdrop, not a portrait: day is a low breath of wind in the canopy, a dark body of moving air with the
crowns' rush just above it and the leaves' faint hush, swelling and settling slowly. Night is stiller air and the
faint shimmer of crickets too far off to tell apart. A bed holds only continuous texture. Anything you could pick out as one thing (a bird, a knock, a creak) is a cue, and
cues are rare: about one a minute or less, most of them far off. Each bed has one hero, the sound that says
"forest" (a songbird by day, an owl by night), allowed a little nearer.

This file is the reference recipe: copy it to recipes/<biome>.py and change the sounds. The build calls `day(s)`
and `night(s)` in loop mode and `cues(s)` in one-shot mode; see README.md, "Writing a recipe".
"""
from lib import *


def day(s):
    # The wind's shape, which every layer follows: a slow random wandering, a new level about every 10 s, about
    # 2 dB from its lowest to its highest, and no gusts. The bed is a backdrop with nothing in it to notice: the
    # owner heard the second version on the Quest (2026-11-17) and found its beds too active, so the gusts and the
    # leaves' puffs are gone and the movement is slower and shallower.
    wind = scale(drift(s.rng("wind"), s.seconds, every=10.0), 0.78, 1.0)

    # The body: dark moving air, a little brighter as the wind rises. Two unrelated noises, one as the middle and
    # one as the sides, are what make it wide (stereo()).
    body = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("body-" + side), corner=90), scale(wind, 160, 300)), wind)
                    for side in "ab"], width=0.7)

    # The crowns: pink noise under about 1.5 kHz, its top moving a little with the wind. Most of what is heard.
    crown = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("crown-" + side)), scale(wind, 900, 1500)), 200),
                           wind) for side in "ab"], width=0.8)

    # The leaves as a whole, too many and too far to hear one: a faint, continuous hush from 1.5 to 4 kHz on a
    # wandering of its own (the second version made them of puffs, which read as a crackle).
    leaf_level = scale(drift(s.rng("leaves"), s.seconds, every=12.0), 0.8, 1.0)
    leaves = stereo(*[apply(band(pink(s.n, s.rng("leaves-" + side)), 1500, 4000), leaf_level) for side in "ab"],
                    width=0.9)

    return mix((body, 0), (crown, -1), (leaves, -16))


def night(s):
    # Stiller air: the same kind of body, slower and shallower in its movement (about 1.4 dB).
    calm = scale(drift(s.rng("calm"), s.seconds, every=12.0), 0.85, 1.0)
    air = stereo(*[apply(moving_lowpass(brown(s.n, s.rng("air-" + side), corner=70), scale(calm, 130, 220)), calm)
                   for side in "ab"], width=0.6)

    # A faint breath in the canopy, so the night is not only a pressure.
    breath = stereo(*[apply(band(pink(s.n, s.rng("breath-" + side)), 250, 1000), calm) for side in "ab"], width=0.8)

    # The crickets, all far off: too many and too distant to tell apart, a faint even shimmer at their pitch,
    # wandering slowly. No caller of its own (the second version's chorus of chirping callers was the busiest
    # thing in the bed; a chirp is a cue's business).
    shimmer_level = scale(drift(s.rng("shimmer"), s.seconds, every=12.0), 0.8, 1.0)
    shimmer = stereo(*[apply(band(white(s.n, s.rng("shimmer-" + side)), 3800, 5400), shimmer_level)
                       for side in "ab"], width=0.9)

    return mix((air, 0), (breath, -10), (shimmer, -12))


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
