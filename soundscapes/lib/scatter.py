"""Many small sounds placed over a bed: granular texture (rustle, drips, rain, crackle) and choruses (insects,
frogs). Each returns a stereo pair of n samples; in loop mode everything wraps round the end, so the result is a
seamless loop.

A *grain* is a function of a random.Random that returns a mono list (lib.voices has makers for them; a lambda
over one is the usual thing). It is called once per grain, so every grain differs.
"""
import math

from .control import drift, stretch
from .core import CONTROL_RATE, RATE, undb
from .mix import pan_gains, place


def _pick_time(rng, n, follow, top):
    """A sample index, uniform, or weighted by a control curve when `follow` is given."""
    if follow is None:
        return rng.randrange(n), 1.0
    m = len(follow)
    while True:
        i = rng.randrange(n)
        v = follow[min(m - 1, i * m // n)]
        if rng.random() * top <= v:
            return i, v / top if top > 0 else 0.0


def scatter(n, rng, count, grain, level=(-12.0, 0.0), pan=(-1.0, 1.0), follow=None, depth=1.0, loop=None):
    """`count` grains at random times over n samples, each at a random level (dB, in `level`) and position (in
    `pan`, -1 left to 1 right). With `follow` (a control curve over the bed) grains come more often where the
    curve is high, and each is also scaled by (curve / its max) ** depth: leaves that rustle with the gusts."""
    left, right = [0.0] * n, [0.0] * n
    top = max(follow) if follow else 1.0
    for _ in range(count):
        at, weight = _pick_time(rng, n, follow, top)
        g = grain(rng)
        k = undb(rng.uniform(*level)) * (weight ** depth if follow else 1.0)
        gl, gr = pan_gains(rng.uniform(*pan))
        place(left, g, at, k * gl, loop)
        place(right, g, at, k * gr, loop)
    return left, right


def chorus(n, rng, voices, voice, rate=(1.0, 2.0), jitter=0.15, level=(-12.0, 0.0), pan=(-1.0, 1.0),
           presence=(0.0, 1.0), every=6.0, loop=None):
    """A chorus of `voices` callers (crickets, frogs, cicadas). Each has its own position, level and repetition
    rate (calls a second, drawn from `rate`), calls on that rate with `jitter` (a share of the period) of
    timing slop, and fades in and out on its own `drift` curve within `presence` (0 is silent, 1 full), with a
    new value about every `every` seconds. `voice(rng)` is called once per caller with that caller's own rng
    and returns its call maker, `call(rng) -> list`, called once per call: draw the caller's character
    (pitch, length) in `voice` and its small call-to-call variation in `call` (see recipes/forest.py,
    `cricket`). In loop mode each voice repeats a whole number of times a loop, so its rhythm is
    seamless too."""
    left, right = [0.0] * n, [0.0] * n
    seconds = n / RATE
    for v in range(voices):
        vr = rng.__class__(rng.getrandbits(32))
        period = 1.0 / vr.uniform(*rate)
        calls = max(1, int(round(seconds / period)))
        period = seconds / calls                       # whole calls a loop
        here = drift(vr, seconds, every, presence[0], presence[1])
        k = undb(vr.uniform(*level))
        gl, gr = pan_gains(vr.uniform(*pan))
        make = voice(vr)                               # this caller's own call maker
        offset = vr.uniform(0, period)
        m = len(here)
        for c in range(calls):
            t = offset + c * period + vr.uniform(-jitter, jitter) * period
            at = int(t * RATE)
            p = here[int(t * CONTROL_RATE) % m]
            if p <= 0.01:
                continue
            g = make(vr)
            place(left, g, at, k * gl * p, loop)
            place(right, g, at, k * gr * p, loop)
    return left, right
