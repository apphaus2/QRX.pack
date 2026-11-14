"""Coloured noise. Every generator returns `n` floats at an RMS of NOISE_RMS (peaks near 1), from the
random.Random it is given, so the same seed gives the same samples. In loop mode the colouring filters run
around the circle (lib.filters), so the noise is itself a seamless loop.
"""
import math

from .core import is_looping
from .filters import _prefix, _warm_length, onepole_lowpass

NOISE_RMS = 0.25


def rms(x):
    return math.sqrt(sum(v * v for v in x) / len(x)) if x else 0.0


def set_rms(x, target=NOISE_RMS):
    """x scaled to RMS `target` (a silent x is returned as it is)."""
    r = rms(x)
    if r < 1e-12:
        return list(x)
    k = target / r
    return [v * k for v in x]


def white(n, rng):
    """Flat noise."""
    r = rng.random
    return set_rms([r() - 0.5 for _ in range(n)])


def pink(n, rng, loop=None):
    """-3 dB/octave noise (Paul Kellet's three-pole filter): softer than white, the base of wind and water."""
    r = rng.random
    w = [r() - 0.5 for _ in range(n)]
    head = _prefix(w, _warm_length(0.99765, n)) if is_looping(loop) else []
    b0 = b1 = b2 = 0.0
    for v in head:
        b0 = 0.99765 * b0 + v * 0.0990460
        b1 = 0.96300 * b1 + v * 0.2965164
        b2 = 0.57000 * b2 + v * 1.0526913
    out = []
    append = out.append
    for v in w:
        b0 = 0.99765 * b0 + v * 0.0990460
        b1 = 0.96300 * b1 + v * 0.2965164
        b2 = 0.57000 * b2 + v * 1.0526913
        append(b0 + b1 + b2 + v * 0.1848)
    return set_rms(out)


def brown(n, rng, corner=60.0, loop=None):
    """-6 dB/octave noise above `corner` Hz and flat below it (a leaky integral of white): rumble, distant
    surf, the body of a wind."""
    r = rng.random
    return set_rms(onepole_lowpass([r() - 0.5 for _ in range(n)], corner, loop))


def blue(n, rng, loop=None):
    """+3 dB/octave noise (the difference of pink): hiss, spray, the top of a rustle."""
    if is_looping(loop):
        p = pink(n, rng, loop)          # differenced around the circle: p[-1] is the last sample
        return set_rms([p[i] - p[i - 1] for i in range(n)])
    p = pink(n + 1, rng, loop)
    return set_rms([p[i + 1] - p[i] for i in range(n)])
