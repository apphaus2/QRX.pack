"""Town: streets, roofs, gardens and park ponds, where most people are.

Day is a town heard from a garden: a low, smooth hum of the whole place, and further off the traffic as a wash
that rises and falls like surf, never one engine; a little open air above it and garden sparrows so faint they
are part of the texture. Nothing harsh and nothing close. Night is the same town thinned out: the hum lower and
quieter, no traffic to speak of, the whisper of a ventilation fan on a roof nearby and the faint, steady tone of
a streetlamp. Everything you could pick out as one thing (a bell, a pigeon, a door, a train) is a cue.
"""
import math

from lib import *


def day(s):
    # The town's hum: dark, smooth, and almost still (a new level about every 8 s, within about 2 dB).
    still = drift(s.rng("hum"), s.seconds, every=8.0, lo=0.8, hi=1.0)
    hum = stereo(*[apply(lowpass(brown(s.n, s.rng("hum-" + side), corner=60), 170), still) for side in "ab"],
                 width=0.5)

    # The traffic, streets away: pink noise kept to the low middle, its brightness and level rising and falling
    # slowly and irregularly, the way a far road swells and eases. Kept shallow, as the forest's wind is, so no
    # swell is a landmark.
    flow = drift(s.rng("flow"), s.seconds, every=4.5, lo=0.0, hi=0.6)
    g = gusts(s.rng("swells"), s.seconds, count=6, rise=(3.0, 5.0), fall=(4.0, 7.0), size=(0.06, 0.14))
    wash_curve = [0.5 + 0.5 * min(1.0, a + b) for a, b in zip(flow, smooth(g, 2.0))]
    wash = stereo(*[apply(highpass(moving_lowpass(pink(s.n, s.rng("wash-" + side)), scale(wash_curve, 450, 1000)),
                                   110), wash_curve) for side in "ab"], width=0.85)

    # Open air above the garden: a faint, even breath in the upper middle, so the bed is not all low.
    air_level = drift(s.rng("air"), s.seconds, every=7.0, lo=0.7, hi=1.0)
    air = stereo(*[apply(band(pink(s.n, s.rng("air-" + side)), 1500, 6000), air_level) for side in "ab"], width=0.9)

    # Garden sparrows: a dozen and a half, a garden or two away, each a soft "cheep" now and then; lower and
    # sparser than the farm's hedgerow, and far under the rest.
    def sparrow(r):
        hz = r.uniform(2800, 3900)
        call = tone(r.uniform(0.06, 0.1), [(0.0, hz * 0.9), (0.4, hz * 1.12), (1.0, hz * 0.95)],
                    harmonics=((1, 1.0), (2, 0.15)), attack=0.008, release=0.03)
        call = distant(call, r.uniform(0.5, 0.8))
        return lambda r2: gain(call, r2.uniform(-3, 0))
    sparrows = chorus(s.n, s.rng("sparrows"), voices=18, voice=sparrow, rate=(0.3, 0.8), jitter=0.35,
                      level=(-6, 0), pan=(-0.9, 0.9), presence=(0.3, 1.0), every=6.0)

    # A trace of high air hiss, for the codec's sake (see the night bed): without it one seed in five came back
    # with a seam at the check's limit.
    hiss = stereo(*[highpass(blue(s.n, s.rng("hiss-" + side)), 7000) for side in "ab"], width=0.9)

    return mix((hum, -10), (wash, 0), (air, -7), (sparrows, -12), (hiss, -24))


def night(s):
    # The hum, lower and thinner than by day.
    still = drift(s.rng("hum"), s.seconds, every=9.0, lo=0.8, hi=1.0)
    hum = stereo(*[apply(lowpass(brown(s.n, s.rng("hum-" + side), corner=50), 120), still) for side in "ab"],
                 width=0.4)

    # A ventilation fan on a roof nearby: an even whisper of air in the middle, the faint note of its blades
    # (two narrow bands) under it. Its level hardly moves: a machine does not breathe.
    whir = drift(s.rng("fan"), s.seconds, every=6.0, lo=0.85, hi=1.0)
    fan = stereo(*[apply(highpass(lowpass(pink(s.n, s.rng("fan-" + side)), 2600), 350), whir) for side in "ab"],
                 width=0.7)
    blades = stereo(*[apply(add(bandpass(white(s.n, s.rng("blade-a-" + side)), 310, q=18),
                                gain(bandpass(white(s.n, s.rng("blade-b-" + side)), 620, q=18), -6)), whir)
                      for side in "ab"], width=0.3)

    # The streetlamp: the faintest steady high tone, a narrow band of noise so it shimmers a little rather than
    # sitting as a pure sine. It is meant to be barely there.
    lamp = stereo(*[bandpass(white(s.n, s.rng("lamp-" + side)), 2400, q=35) for side in "ab"], width=0.2)

    # Very far off, what is left of the traffic: a dark, slow wash well under the hum.
    flow = drift(s.rng("flow"), s.seconds, every=6.0, lo=0.6, hi=1.0)
    wash = stereo(*[apply(highpass(lowpass(pink(s.n, s.rng("wash-" + side)), 500), 100), flow) for side in "ab"],
                  width=0.85)

    # A trace of high air hiss. Hardly audible, but a bed with almost nothing above 8 kHz came back from the
    # codec with a seam that failed its check (the step across the wrap is measured against the steps around it,
    # which in a dark bed are tiny); a little energy up here gives that measure something to compare with.
    hiss = stereo(*[highpass(blue(s.n, s.rng("hiss-" + side)), 7000) for side in "ab"], width=0.9)

    return mix((hum, -2), (wash, -8), (fan, -5), (blades, -12), (lamp, -22), (hiss, -24))


def bike_bell(r):
    """A bicycle bell a street away: a quick ring-ring, the hammer striking a small bright dome."""
    dome = ((1.0, 1.0, 0.3), (1.47, 0.5, 0.18), (2.09, 0.3, 0.1), (2.9, 0.12, 0.06))
    hz = r.uniform(2700, 2950)
    ring = silence(1.2)
    t = 0.0
    for burst in range(2):
        for k in range(5):
            overlay(ring, bell(hz, 0.5, dome), t + k * 0.045, gain=1.0 - 0.1 * k)
        t += 0.45
    return distant(ring, 0.35)


def pigeon(r):
    """A pigeon on a roof: a soft rolling "hoo-hrroo-hoo", the middle note trembling."""
    hz = r.uniform(300, 340)
    a = tone(0.32, (hz * 0.95, hz * 1.08), harmonics=((1, 1.0), (2, 0.25)), attack=0.04, release=0.12)
    b = tone(0.55, [(0.0, hz * 1.05), (0.4, hz * 1.15), (1.0, hz * 0.9)], harmonics=((1, 1.0), (2, 0.3)),
             attack=0.04, release=0.15, tremolo=(26, 0.55))
    c = tone(0.4, (hz * 1.0, hz * 0.88), harmonics=((1, 1.0), (2, 0.25)), attack=0.04, release=0.2)
    return seq(a, silence(0.12), b, silence(0.15), c)


def church_bell(r):
    """A church or clock bell across the town: one stroke, its hum ringing on long after."""
    partials = ((0.5, 0.6, 2.4), (1.0, 1.0, 1.6), (1.19, 0.5, 1.1), (1.5, 0.35, 0.9), (2.0, 0.45, 0.7),
                (2.52, 0.15, 0.4), (3.0, 0.1, 0.3))
    return distant(bell(r.uniform(285, 300), 2.9, partials), 0.55)


def shut(r):
    """A wooden door closing: a dull puff of low-middle noise with a short woody ring in it. (knock()'s own
    thump sits at a fifth of its pitch, about 35 Hz for a door, which the codec drops: the cue then came out
    9 dB quieter than it was made.)"""
    return add(noise_burst(r, 0.22, lo=90, hi=900, attack=0.002, release=0.18, curve=2.5),
               gain(knock(r, 320, 0.22, q=4, body=0.0), -3))


def door(r):
    """A front door down the street: the handle, a short creak, and the door shut with a soft thump."""
    return distant(seq(knock(r, 2100, 0.06, q=12, body=0.1), silence(0.12),
                       creak(r, 0.45, rate=(30, 60), hz=(600, 1200), q=6), silence(0.08),
                       shut(r)), 0.3)


def ball(r):
    """A ball dropped in a garden: bounces coming quicker and quieter until it rolls away."""
    out, t, gap, g = silence(2.0), 0.0, 0.42, 1.0
    for _ in range(7):
        hit = add(knock(r, r.uniform(380, 440), 0.12, q=5, body=0.0),
                  gain(noise_burst(r, 0.06, lo=150, hi=1200, attack=0.001, release=0.05, curve=2.0), -4))
        overlay(out, hit, t, gain=g)
        t += gap
        gap *= 0.74
        g *= 0.72
    return distant(out, 0.25)


def horn(r):
    """A car horn many streets away: one short muted toot, mostly its low note."""
    toot = tone(0.32, 392, harmonics=((1, 1.0), (1.26, 0.6), (2, 0.4), (2.52, 0.2), (3, 0.15)), attack=0.02,
                release=0.08)
    return distant(lowpass(toot, 1400), 0.8)


def train(r):
    """A train far off at night: a long low rumble swelling and fading, with the faint clack of the rails."""
    rumble = noise_burst(r, 3.4, lo=50, hi=500, attack=1.3, release=1.6)
    clacks = silence(3.4)
    t = 0.4
    while t < 2.9:
        for k in range(2):
            overlay(clacks, knock(r, r.uniform(700, 900), 0.06, q=6, body=0.3), t + k * 0.14,
                    gain=0.25 * math.sin(math.pi * t / 3.4))
        t += r.uniform(0.85, 1.0)
    return distant(add(rumble, clacks), 0.6)


def cat(r):
    """A cat in a yard: one meow, rising and falling, nasal."""
    meow = tone(0.75, [(0.0, 520), (0.3, 820), (0.65, 760), (1.0, 470)],
                harmonics=((1, 1.0), (2, 0.6), (3, 0.4), (4, 0.2), (5, 0.1)), attack=0.04, release=0.2,
                vibrato=(6, 0.01), breath=0.03, rng=r)
    return distant(peak(meow, 1500, q=1.5, gain_db=5), 0.35)


def footsteps(r):
    """Footsteps passing on the pavement: eight steps coming up and going away again."""
    out = silence(4.0)
    t = 0.0
    for k in range(8):
        g = math.sin(math.pi * (k + 0.5) / 8) ** 1.5
        step = add(noise_burst(r, 0.07, lo=200, hi=3000, attack=0.002, release=0.05, curve=2.0),
                   gain(knock(r, r.uniform(320, 380), 0.07, q=3, body=0.6), -4))
        overlay(out, step, t, gain=g)
        t += r.uniform(0.44, 0.5)
    return distant(out, 0.3)


def chime(r):
    """A wind chime on a porch: a handful of tubes touched by a breath of wind."""
    notes = [1320, 1480, 1760, 1980, 2220]
    tube = ((1.0, 1.0, 0.9), (2.76, 0.25, 0.35), (5.4, 0.08, 0.15))
    out = silence(3.3)
    for _ in range(r.randint(5, 7)):
        overlay(out, bell(r.choice(notes), 1.4, tube), r.uniform(0.0, 1.8), gain=r.uniform(0.4, 1.0))
    return out


def drip(r):
    """A gutter dripping after rain: a few drops into a pool, irregular."""
    out = silence(3.2)
    t = 0.0
    for _ in range(r.randint(5, 7)):
        hz = r.uniform(900, 1400)
        plink = [a * b for a, b in zip(chirp(0.06, hz, hz * 2.2), decay(0.06, 0.018))]
        overlay(out, plink, t, gain=r.uniform(0.6, 1.0))
        t += r.uniform(0.3, 0.6)
    return out


def cues(s):
    r = s.rng
    return [
        cue("bicycle-bell", space(bike_bell(r("bike")), r("bike-space"), 0.6, 0.2),
            beds=["day"], every=[40, 110], level=-4, spread=0.8),
        cue("pigeon", space(pigeon(r("pigeon")), r("pigeon-space"), 0.5, 0.15),
            beds=["day"], every=[20, 60], level=-2, spread=0.8),
        # The church clock strikes by day and by night.
        cue("church-bell", space(church_bell(r("church")), r("church-space"), 0.9, 0.3),
            beds=["day", "night"], every=[60, 180], level=-6, spread=1.0),
        cue("door", space(door(r("door")), r("door-space"), 0.4, 0.15),
            beds=["day"], every=[45, 120], level=-4, spread=0.7),
        cue("ball", space(ball(r("ball")), r("ball-space"), 0.4, 0.15),
            beds=["day"], every=[50, 140], level=-4, spread=0.7),
        cue("horn", space(horn(r("horn")), r("horn-space"), 1.0, 0.35),
            beds=["day"], every=[60, 160], level=-9, spread=1.0),

        cue("train", train(r("train")),
            beds=["night"], every=[70, 180], level=-6, spread=1.0),
        cue("cat", space(cat(r("cat")), r("cat-space"), 0.6, 0.2),
            beds=["night"], every=[50, 140], level=-4, spread=0.8),
        cue("footsteps", space(footsteps(r("steps")), r("steps-space"), 0.4, 0.15),
            beds=["night"], every=[40, 110], level=-4, spread=0.6),
        cue("wind-chime", space(chime(r("chime")), r("chime-space"), 0.5, 0.15),
            beds=["night"], every=[35, 90], level=-5, spread=0.7),
        cue("gutter-drip", space(drip(r("drip")), r("drip-space"), 0.4, 0.15),
            beds=["night"], every=[30, 80], level=-5, spread=0.6),
    ]
