"""What the build does to a recipe's output before it is encoded. A recipe does not call these."""
import re

from .core import BED_PEAK_DB, BED_RMS_DB, CUE_LOUD_DB, CUE_PEAK_DB, CUE_SECONDS, RATE, db, undb
from .filters import highpass
from .mix import remove_dc, soft_limit
from .voices import trim

BED_HIGHPASS = 50.0  # Hz
CUE_ID = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
CUE_PAD = 0.02      # seconds of true silence before and after every cue, so the codec's ringing has room
CUE_FADE = 0.003    # seconds of fade at each end of the sound itself


def _power(left, right):
    return (sum(v * v for v in left) + sum(v * v for v in right)) / (2 * len(left))


def bed(pair, n, name):
    """A recipe's (left, right) made into a bed: the DC and what is under BED_HIGHPASS taken out, the RMS set to
    BED_RMS_DB, and anything near the peak limit bent under it by the soft limiter (then the RMS set again)."""
    if not (isinstance(pair, (tuple, list)) and len(pair) == 2):
        raise ValueError("%s must return (left, right)" % name)
    left, right = [float(v) for v in pair[0]], [float(v) for v in pair[1]]
    if len(left) != n or len(right) != n:
        raise ValueError("%s returned %d and %d samples; a bed is exactly s.n = %d" % (name, len(left), len(right), n))
    # afconvert's Opus encoder drops most of what is under 60 Hz (measured: -11 dB at 10-30 Hz, -4.5 dB at 30-60),
    # and a phone plays none of it, so it is taken out here, where the RMS is set, rather than lost in the codec.
    left, right = highpass(remove_dc(left), BED_HIGHPASS, loop=True), highpass(remove_dc(right), BED_HIGHPASS, loop=True)
    for _ in range(4):
        p = _power(left, right)
        if p <= 0:
            raise ValueError("%s is silent" % name)
        k = undb(BED_RMS_DB) / p ** 0.5
        left, right = [v * k for v in left], [v * k for v in right]
        top = max(max(map(abs, left)), max(map(abs, right)))
        if db(top) < BED_PEAK_DB - 1.0:
            break
        left, right = soft_limit(left, BED_PEAK_DB - 0.8), soft_limit(right, BED_PEAK_DB - 0.8)
    return left, right


def regain(left, right, gain_db):
    """A finished bed made `gain_db` louder (or softer), still under the peak limit."""
    k = undb(gain_db)
    left, right = [v * k for v in left], [v * k for v in right]
    top = max(max(map(abs, left)), max(map(abs, right)))
    if db(top) >= BED_PEAK_DB - 1.0:
        left, right = soft_limit(left, BED_PEAK_DB - 0.8), soft_limit(right, BED_PEAK_DB - 0.8)
    return left, right


def cue(c, name):
    """A recipe's cue made ready: trimmed, faded at both ends, scaled so its loudest 100 ms is CUE_LOUD_DB (any
    peak that leaves pushed towards CUE_PEAK_DB by the soft limiter), and padded with silence."""
    if not CUE_ID.match(c.id):
        raise ValueError("%s: cue id %r must be lower-case words joined by hyphens" % (name, c.id))
    if not c.beds or any(b not in ("day", "night") for b in c.beds):
        raise ValueError("%s: cue %s: beds must be 'day', 'night' or both" % (name, c.id))
    lo, hi = c.every
    if not 0 < lo <= hi:
        raise ValueError("%s: cue %s: every must be [min, max] seconds with 0 < min <= max" % (name, c.id))
    if not 0 <= c.spread <= 1:
        raise ValueError("%s: cue %s: spread is 0..1" % (name, c.id))
    x = trim([float(v) for v in c.samples])
    if not x:
        raise ValueError("%s: cue %s is silent" % (name, c.id))
    x = remove_dc(x)
    f = min(int(CUE_FADE * RATE), len(x) // 4)
    for i in range(f):
        g = i / f
        x[i] *= g
        x[-1 - i] *= g
    w, hop = int(0.1 * RATE), int(0.025 * RATE)
    loud = max(sum(v * v for v in x[i:i + w]) / w for i in range(0, max(1, len(x) - w + 1), hop)) ** 0.5
    k = undb(CUE_LOUD_DB) / loud
    x = [v * k for v in x]
    if db(max(map(abs, x))) > CUE_PEAK_DB - 6.0:
        x = soft_limit(x, CUE_PEAK_DB, 6.0)
    pad = [0.0] * int(CUE_PAD * RATE)
    out = pad + x + pad
    seconds = len(out) / RATE
    if not CUE_SECONDS[0] <= seconds <= CUE_SECONDS[1]:
        raise ValueError("%s: cue %s is %.2f s with its padding; a cue is %.1f to %.1f s"
                         % (name, c.id, seconds, CUE_SECONDS[0], CUE_SECONDS[1]))
    return out
