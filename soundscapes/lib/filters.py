"""Filters: one-pole, biquad (RBJ cookbook) and a one-pole whose cutoff moves.

In loop mode (lib.core) every filter runs around the circle: it first runs over the end of the buffer, long
enough for its state to forget where it started (until its impulse response has fallen 140 dB), and then over
the whole buffer, so the state at sample 0 is the state after the last sample. That is why a filtered loop has
no seam. In one-shot mode it starts from rest. Each returns a new list; none changes its input.
"""
import math

from .core import RATE, is_looping

_FORGET = math.log(1e-7)   # the warm-up runs until the impulse response is 140 dB down


def _warm_length(radius, n):
    """Samples for a pole of this radius (0..1) to forget its start, at most a few laps of the buffer."""
    if radius <= 0:
        return 8
    if radius >= 1:
        return 4 * n
    return min(4 * n, int(_FORGET / math.log(radius)) + 8)


def _prefix(x, warm):
    """The samples to run before x so that, in loop mode, the state at x[0] is the loop's own."""
    n = len(x)
    if warm <= 0 or n == 0:
        return []
    laps, rest = divmod(warm, n)
    return (x[n - rest:] if rest else []) + x * laps


def onepole_lowpass(x, hz, loop=None):
    """A gentle 6 dB/octave low-pass at `hz`."""
    a = math.exp(-2 * math.pi * hz / RATE)
    head = _prefix(x, _warm_length(a, len(x))) if is_looping(loop) else []
    y, b, out = 0.0, 1 - a, []
    append = out.append
    for v in head:
        y = a * y + b * v
    for v in x:
        y = a * y + b * v
        append(y)
    return out


def onepole_highpass(x, hz, loop=None):
    """The complement of onepole_lowpass: x minus its low-passed self."""
    return [v - l for v, l in zip(x, onepole_lowpass(x, hz, loop))]


def _biquad(x, b0, b1, b2, a1, a2, loop):
    # pole radius: sqrt(a2) for a complex pair, the larger root for real ones
    disc = a1 * a1 - 4 * a2
    radius = math.sqrt(abs(a2)) if disc < 0 else max(abs((-a1 + math.sqrt(disc)) / 2), abs((-a1 - math.sqrt(disc)) / 2))
    head = _prefix(x, _warm_length(radius, len(x))) if is_looping(loop) else []
    x1 = x2 = y1 = y2 = 0.0
    for v in head:
        y = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, v, y1, y
    out = []
    append = out.append
    for v in x:
        y = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, v, y1, y
        append(y)
    return out


def _rbj(kind, hz, q, gain_db=0.0):
    hz = min(max(hz, 5.0), 0.49 * RATE)
    w = 2 * math.pi * hz / RATE
    cw, sw = math.cos(w), math.sin(w)
    alpha = sw / (2 * q)
    if kind == "lowpass":
        b = ((1 - cw) / 2, 1 - cw, (1 - cw) / 2); a = (1 + alpha, -2 * cw, 1 - alpha)
    elif kind == "highpass":
        b = ((1 + cw) / 2, -(1 + cw), (1 + cw) / 2); a = (1 + alpha, -2 * cw, 1 - alpha)
    elif kind == "bandpass":       # 0 dB at the centre
        b = (alpha, 0.0, -alpha); a = (1 + alpha, -2 * cw, 1 - alpha)
    elif kind == "highshelf":
        A = 10 ** (gain_db / 40)
        sa = 2 * math.sqrt(A) * alpha
        b = (A * ((A + 1) + (A - 1) * cw + sa), -2 * A * ((A - 1) + (A + 1) * cw), A * ((A + 1) + (A - 1) * cw - sa))
        a = ((A + 1) - (A - 1) * cw + sa, 2 * ((A - 1) - (A + 1) * cw), (A + 1) - (A - 1) * cw - sa)
    elif kind == "peak":
        A = 10 ** (gain_db / 40)
        b = (1 + alpha * A, -2 * cw, 1 - alpha * A); a = (1 + alpha / A, -2 * cw, 1 - alpha / A)
    else:
        raise ValueError(kind)
    return b[0] / a[0], b[1] / a[0], b[2] / a[0], a[1] / a[0], a[2] / a[0]


def lowpass(x, hz, q=0.7071, loop=None):
    """A 12 dB/octave low-pass; q above 0.7 adds a bump at the cutoff."""
    return _biquad(x, *_rbj("lowpass", hz, q), loop)


def highpass(x, hz, q=0.7071, loop=None):
    """A 12 dB/octave high-pass."""
    return _biquad(x, *_rbj("highpass", hz, q), loop)


def bandpass(x, hz, q=1.0, loop=None):
    """A resonant band-pass, 0 dB at `hz`; higher q is narrower (q 10 rings like a struck thing)."""
    return _biquad(x, *_rbj("bandpass", hz, q), loop)


def peak(x, hz, q=1.0, gain_db=6.0, loop=None):
    """A bell-shaped boost or cut of `gain_db` at `hz`."""
    return _biquad(x, *_rbj("peak", hz, q, gain_db), loop)


def highshelf(x, hz, gain_db, q=0.7071, loop=None):
    """Everything above `hz` raised (or lowered) by `gain_db`."""
    return _biquad(x, *_rbj("highshelf", hz, q, gain_db), loop)


def band(x, lo, hi, loop=None):
    """Keeps lo..hi Hz: a high-pass at lo then a low-pass at hi (12 dB/octave each side)."""
    return lowpass(highpass(x, lo, loop=loop), hi, loop=loop)


def moving_lowpass(x, hz, loop=None):
    """A one-pole low-pass whose cutoff follows `hz`, a control curve in Hz (lib.control; any length, it is
    stretched over x). Wind that brightens as it rises: moving_lowpass(noise, scale(gust, 300, 2500))."""
    n, m = len(x), len(hz)
    if m == 0 or n == 0:
        return list(x)
    coef = [math.exp(-2 * math.pi * min(max(h, 1.0), 0.45 * RATE) / RATE) for h in hz]
    looping = is_looping(loop)
    step = m / n
    y = 0.0
    if looping:     # warm up over the last part of the loop with the matching coefficients
        warm = min(n, _warm_length(max(coef), n))
        for i in range(n - warm, n):
            a = coef[int(i * step) % m]
            y = a * y + (1 - a) * x[i]
    out = []
    append = out.append
    for i, v in enumerate(x):
        a = coef[int(i * step) % m] if looping else coef[min(m - 1, int(i * step))]
        y = a * y + (1 - a) * v
        append(y)
    return out


def allpass(x, delay, g=0.5, loop=None):
    """A Schroeder all-pass of `delay` samples: changes phase, not spectrum (lib.mix.decorrelate chains them)."""
    n = len(x)
    out = [0.0] * n
    if is_looping(loop):
        # y[i] = -g x[i] + x[i-d] + g y[i-d], run round the circle until the feedback has died away
        laps = max(1, int(math.ceil(_warm_length(abs(g) ** (1.0 / max(delay, 1)), n) / n)))
        y = [0.0] * n
        for _ in range(laps + 1):
            for i in range(n):
                j = i - delay
                y[i] = -g * x[i] + x[j % n] + g * y[j % n]
        return y
    for i in range(n):
        j = i - delay
        out[i] = -g * x[i] + (x[j] + g * out[j] if j >= 0 else 0.0)
    return out
