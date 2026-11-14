"""Control curves: slow movement (gusts, swells, a chorus thinning and filling) at CONTROL_RATE points a second.

A curve is a plain list of floats, point j at time j / CONTROL_RATE. Curves for a bed are periodic over the
bed: `drift` and `gusts` wrap round the end and `swell` takes whole cycles, so a curve's last point leads
smoothly into its first. `stretch` brings a curve to audio rate and `apply` multiplies a signal by one.

Irregular, not periodic within the loop: a bed must not have one movement a listener could learn, so prefer
`drift` and `gusts` (random times and sizes) to `swell` (a sine) for anything you can hear move.
"""
import math

from .core import CONTROL_RATE, is_looping


def points(seconds):
    """The number of points in a curve of this length."""
    return max(2, int(round(seconds * CONTROL_RATE)))


def constant(seconds, value):
    return [float(value)] * points(seconds)


def drift(rng, seconds, every=4.0, lo=0.0, hi=1.0, jitter=0.6):
    """Smooth random wandering between lo and hi: a new value about every `every` seconds (the knot times are
    jittered by up to `jitter` of the spacing), joined by cubic Hermite curves, periodic over `seconds`.
    The result can overshoot lo..hi a little between knots; it is clamped to them."""
    m = points(seconds)
    k = max(3, int(round(seconds / every)))
    gap = m / k
    times = sorted((i + rng.uniform(-jitter / 2, jitter / 2)) * gap for i in range(k))
    values = [rng.uniform(lo, hi) for _ in range(k)]
    # tangents from the neighbours, around the circle
    tangents = []
    for i in range(k):
        t0, t1 = times[i - 1] - (m if i == 0 else 0), times[(i + 1) % k] + (m if i == k - 1 else 0)
        tangents.append((values[(i + 1) % k] - values[i - 1]) / (t1 - t0))
    out = [0.0] * m
    for i in range(k):
        a, b = times[i], times[(i + 1) % k] + (m if i == k - 1 else 0)
        pa, pb, ma, mb, span = values[i], values[(i + 1) % k], tangents[i], tangents[(i + 1) % k], b - a
        j = int(math.ceil(a))
        while j < b:
            u = (j - a) / span
            u2, u3 = u * u, u * u * u
            v = (2 * u3 - 3 * u2 + 1) * pa + (u3 - 2 * u2 + u) * span * ma + (-2 * u3 + 3 * u2) * pb + (u3 - u2) * span * mb
            out[j % m] = min(hi, max(lo, v))
            j += 1
    return out


def swell(seconds, cycles, lo=0.0, hi=1.0, phase=0.0):
    """A sine between lo and hi with a whole number of `cycles` in `seconds` (so it loops). Regular: use it
    under something else, or for movement too slow to notice (one or two cycles a bed)."""
    m = points(seconds)
    c = max(1, int(round(cycles)))
    return [lo + (hi - lo) * 0.5 * (1 - math.cos(2 * math.pi * c * j / m + phase)) for j in range(m)]


def gusts(rng, seconds, count, rise=(1.5, 4.0), fall=(2.5, 7.0), size=(0.35, 1.0), loop=None):
    """`count` swells at random times: each rises over `rise` seconds and dies over `fall` (half-cosine
    shoulders), with a random height in `size`. Overlaps add; the sum is clamped to 1. Zero between gusts,
    so add a floor: [0.2 + 0.8 * g for g in gusts(...)]. In loop mode a gust near the end wraps to the start."""
    m = points(seconds)
    out = [0.0] * m
    wrap = is_looping(loop)
    for _ in range(count):
        start = rng.uniform(0, m)
        up = rng.uniform(*rise) * CONTROL_RATE
        down = rng.uniform(*fall) * CONTROL_RATE
        height = rng.uniform(*size)
        j = int(start)
        end = start + up + down
        while j < end:
            t = j - start
            if t >= 0:
                v = 0.5 * (1 - math.cos(math.pi * t / up)) if t < up else 0.5 * (1 + math.cos(math.pi * (t - up) / down))
                if wrap:
                    out[j % m] += height * v
                elif j < m:
                    out[j] += height * v
            j += 1
    return [min(1.0, v) for v in out]


def scale(curve, lo, hi):
    """A 0..1 curve mapped onto lo..hi."""
    return [lo + (hi - lo) * v for v in curve]


def smooth(curve, seconds, loop=None):
    """A curve with its quick movement taken out: a centred moving average `seconds` wide."""
    m = len(curve)
    w = max(1, int(seconds * CONTROL_RATE))
    half = w // 2
    wrap = is_looping(loop)
    out = []
    for j in range(m):
        if wrap:
            vals = [curve[(j + d) % m] for d in range(-half, half + 1)]
        else:
            vals = curve[max(0, j - half): min(m, j + half + 1)]
        out.append(sum(vals) / len(vals))
    return out


def stretch(curve, n, loop=None):
    """A curve linearly interpolated to n points (audio rate). In loop mode the last stretch runs back to the
    first point, so the result is periodic."""
    m = len(curve)
    if m == n:
        return list(curve)
    wrap = is_looping(loop)
    out = []
    append = out.append
    step = m / n
    last = m - 1
    for i in range(n):
        p = i * step
        j = int(p)
        f = p - j
        a = curve[j]
        b = curve[(j + 1) % m] if wrap else curve[min(last, j + 1)]
        append(a + (b - a) * f)
    return out


def apply(x, curve, loop=None):
    """x multiplied, sample by sample, by a curve stretched to its length."""
    env = stretch(curve, len(x), loop)
    return [v * e for v, e in zip(x, env)]
