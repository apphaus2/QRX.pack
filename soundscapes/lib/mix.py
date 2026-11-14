"""Mixing: levels, stereo placement and width, decorrelation, and the soft limiter.

A stereo signal is a pair (left, right) of equal-length lists; a mono one is a list.
"""
import math

from .core import RATE, is_looping, undb
from .filters import allpass


def gain(x, db):
    """x louder or softer by `db`."""
    k = undb(db)
    return [v * k for v in x]


def add(*signals):
    """The sum of mono lists of one length."""
    return [sum(vs) for vs in zip(*signals)]


def mix(*layers):
    """The sum of stereo layers, each given as (pair, db) or as a pair at 0 dB:
    mix((wind, 0), (leaves, -6), crickets)."""
    left = right = None
    for layer in layers:
        if len(layer) == 2 and isinstance(layer[1], (int, float)):
            (l, r), d = layer
        else:
            (l, r), d = layer, 0.0
        k = undb(d)
        if left is None:
            left, right = [v * k for v in l], [v * k for v in r]
        else:
            left = [a + v * k for a, v in zip(left, l)]
            right = [a + v * k for a, v in zip(right, r)]
    return left, right


def pan_gains(position):
    """Equal-power (left, right) gains for a position from -1 (left) through 0 (centre) to 1 (right)."""
    p = (min(1.0, max(-1.0, position)) + 1) * math.pi / 4
    return math.cos(p), math.sin(p)


def pan(x, position):
    """A mono signal placed in the stereo field."""
    gl, gr = pan_gains(position)
    return [v * gl for v in x], [v * gr for v in x]


def stereo(a, b, width=0.6):
    """Two independent mono signals of similar level made into one wide stereo layer: a is the middle, b the
    sides. width 0 is mono, 1 is two unrelated channels; the left/right correlation is (1 - w^2) / (1 + w^2),
    about 0.47 at 0.6. Independent noise for b is the cheapest decorrelation there is."""
    k = 1 / math.sqrt(1 + width * width)
    return [(m + width * s) * k for m, s in zip(a, b)], [(m - width * s) * k for m, s in zip(a, b)]


def widen(pair, width=0.6):
    """A stereo pair's width changed: 0 folds it to mono, 1 keeps it, above 1 widens (mid/side)."""
    l, r = pair
    return ([(a + b) / 2 + width * (a - b) / 2 for a, b in zip(l, r)],
            [(a + b) / 2 - width * (a - b) / 2 for a, b in zip(l, r)])


def decorrelate(x, rng, stages=3, loop=None):
    """A copy of x with the same spectrum and scrambled phase (a chain of all-passes with random delays of
    2 to 12 ms): stereo(x, decorrelate(x, rng)) widens one source without a second noise. Slow on long
    beds (a second or two a stage); independent noise through stereo() is cheaper when you have it."""
    y = list(x)
    for _ in range(stages):
        y = allpass(y, int(rng.uniform(0.002, 0.012) * RATE), rng.uniform(0.4, 0.7), loop)
    return y


def remove_dc(x):
    """x minus its mean (for a loop, the mean over the loop: still seamless)."""
    m = sum(x) / len(x) if x else 0.0
    return [v - m for v in x]


def soft_limit(x, ceiling_db=-3.5, knee_db=6.0):
    """Leaves everything below `ceiling_db - knee_db` alone and bends what is above it smoothly towards the
    ceiling, which it never reaches. Memoryless, so a seamless loop stays seamless."""
    c = undb(ceiling_db)
    t = undb(ceiling_db - knee_db)
    span = c - t
    out = []
    append = out.append
    for v in x:
        a = abs(v)
        if a <= t:
            append(v)
        else:
            y = t + span * math.tanh((a - t) / span)
            append(y if v > 0 else -y)
    return out


def place(buf, x, start, gain=1.0, loop=None):
    """Adds x into buf from sample `start`, in place. In loop mode what runs past the end wraps to the start;
    in one-shot mode it is cut."""
    n, m = len(buf), len(x)
    if m == 0 or n == 0:
        return buf
    start = int(start) % n if is_looping(loop) else int(start)
    pos, i = start, 0
    while i < m:
        if pos >= n:
            if not is_looping(loop):
                break
            pos = 0
        if pos < 0:
            skip = -pos
            i += skip
            pos = 0
            continue
        take = min(m - i, n - pos)
        buf[pos:pos + take] = [a + v * gain for a, v in zip(buf[pos:pos + take], x[i:i + take])]
        pos += take
        i += take
    return buf
