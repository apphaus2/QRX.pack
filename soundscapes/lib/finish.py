"""What the build does to a recipe's output before it is encoded. A recipe does not call these."""
import math, re

from .core import BED_LUFS, BED_PEAK_DB, BRIGHTNESS, CUE_LOUD_DB, CUE_PEAK_DB, CUE_SECONDS, RATE, db, undb
from .filters import highpass, highshelf
from .measure import band_signals, loudness, shares
from .mix import remove_dc, soft_limit
from .voices import trim

BED_HIGHPASS = 50.0  # Hz
CUE_ID = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
CUE_PAD = 0.02      # seconds of true silence before and after every cue, so the codec's ringing has room
CUE_FADE = 0.003    # seconds of fade at each end of the sound itself


SOFTEN_MARGIN = (3.0, 1.0)   # percentage points under the brightness ceilings the softening aims for (2k, 8k)
SOFTEN_MOST = 12.0           # dB: the deepest either shelf may cut


def _mid(left, right):
    return [(a + b) * 0.5 for a, b in zip(left, right)]


def _shelf_db(share, target):
    """The shelf gain (dB, <= 0) that would bring a band holding `share` of the energy down to `target`, were the
    shelf a brick wall (it is not, so the softening measures again and repeats)."""
    if share <= target or share >= 1:
        return 0.0
    return max(-SOFTEN_MOST, 10 * math.log10(target * (1 - share) / ((1 - target) * share)))


def _shelves(left, right, above2, above8, part, cut2, cut8):
    """One round of shelf cuts from measured shares (0..1); returns (left, right, cut2, cut8, changed)."""
    top2, top8 = BRIGHTNESS[part]
    want2, want8 = (top2 - SOFTEN_MARGIN[0]) / 100, (top8 - SOFTEN_MARGIN[1]) / 100
    # a shelf is not a brick wall, so each round cuts a third more than the share alone asks for
    g8 = max(1.33 * _shelf_db(above8, want8), -SOFTEN_MOST - cut8)
    g2 = max(1.33 * _shelf_db(above2, want2), -SOFTEN_MOST - cut2)
    changed = False
    if g8 <= -0.2:
        left, right = highshelf(left, 8000.0, g8, loop=True), highshelf(right, 8000.0, g8, loop=True)
        cut8 += g8
        changed = True
    if g2 <= -0.2:
        left, right = highshelf(left, 2000.0, g2, loop=True), highshelf(right, 2000.0, g2, loop=True)
        cut2 += g2
        changed = True
    return left, right, cut2, cut8, changed


def soften(left, right, part, cut2=0.0, cut8=0.0, bands=None):
    """The bed with its top taken down by high shelves at 8 kHz and at 2 kHz until its shares of energy above them
    are under BRIGHTNESS[part] with a margin. Returns (left, right, cut2_db, cut8_db); a bed already under them
    comes back unchanged. `bands` (percent, as lib.measure.bed gives them) starts from a decoded file's
    measures instead of the bed's own, for a second pass after the codec. A recipe that wants no softening keeps
    its own top under the ceiling."""
    for _ in range(8):
        if bands is not None:
            above2, above8 = (bands["2k-8k"] + bands[">8k"]) / 100, bands[">8k"] / 100
            bands = None
        else:
            sh = shares(band_signals(_mid(left, right)))
            above2, above8 = sh["2k-8k"] + sh[">8k"], sh[">8k"]
        left, right, cut2, cut8, changed = _shelves(left, right, above2, above8, part, cut2, cut8)
        if not changed:
            break
    return left, right, cut2, cut8


def level(left, right):
    """The bed set to BED_LUFS, anything near the peak limit bent under it (then the loudness set again)."""
    for _ in range(4):
        k = undb(BED_LUFS - loudness(left, right))
        left, right = [v * k for v in left], [v * k for v in right]
        top = max(max(map(abs, left)), max(map(abs, right)))
        if db(top) < BED_PEAK_DB - 1.0:
            break
        left, right = soft_limit(left, BED_PEAK_DB - 0.8), soft_limit(right, BED_PEAK_DB - 0.8)
    return left, right


def bed(pair, n, name, part="day"):
    """A recipe's (left, right) made into a bed: the DC and what is under BED_HIGHPASS taken out, the top softened
    under BRIGHTNESS[part] (`soften`), the loudness set to BED_LUFS, and anything near the peak limit bent under
    it by the soft limiter (then the loudness set again). Returns (left, right, notes): notes says how much the
    softening cut."""
    if not (isinstance(pair, (tuple, list)) and len(pair) == 2):
        raise ValueError("%s must return (left, right)" % name)
    left, right = [float(v) for v in pair[0]], [float(v) for v in pair[1]]
    if len(left) != n or len(right) != n:
        raise ValueError("%s returned %d and %d samples; a bed is exactly s.n = %d" % (name, len(left), len(right), n))
    # afconvert's Opus encoder drops most of what is under 60 Hz (measured: -11 dB at 10-30 Hz, -4.5 dB at 30-60),
    # and a phone plays none of it, so it is taken out here, where the level is set, rather than lost in the codec.
    left, right = highpass(remove_dc(left), BED_HIGHPASS, loop=True), highpass(remove_dc(right), BED_HIGHPASS, loop=True)
    if max(max(map(abs, left)), max(map(abs, right))) <= 0:
        raise ValueError("%s is silent" % name)
    left, right, cut2, cut8 = soften(left, right, part)
    left, right = level(left, right)
    return left, right, {"softened2k": round(cut2, 1), "softened8k": round(cut8, 1)}


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
