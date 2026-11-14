"""Numbers that stand in for ears: what the build prints after every file and what `--check` holds them to.

Beds (stereo, measured on the decoded file):
  peak     the highest sample, dBFS                          under BED_PEAK_DB (-3)
  rms      the mean power of both channels, dBFS             within BED_RMS_TOLERANCE of BED_RMS_DB (-26 +- 1)
  dc       the larger channel mean, dBFS                     under -50
  corr     left/right correlation                            0.05 to 0.90: not mono, not anti-phase
  seam     the step across the wrap (last sample to first) over four times the RMS of the sample-to-sample
           steps in the 50 ms either side of it, the larger of the two channels; and `slope`, the same for the
           second difference (a kink)                       each at most 1.0: the seam moves no more than the
                                                             file's own ordinary movement there
  lufs     loudness after the K-weighting of ITU-R BS.1770 (a high-pass at 38 Hz, +4 dB above 1.5 kHz), ungated:
           how loud the bed sounds, where rms is how much energy it has (no limit; a bed whose energy is mostly
           rumble sounds quieter than its rms says, so compare biomes by this)
  bands    share of the energy below 250 Hz, 250 Hz-2 kHz, 2-8 kHz and above 8 kHz (a fingerprint; no limit)
  spread   the loudest 250 ms window over the median window, dB (of the whole signal)      at most SPREAD_DB
  stand    the largest amount by which one 250 ms window rises above its surroundings (the median of the
           windows 0.5 to 2 s either side, around the loop), dB, over the whole signal and each band holding
           5% or more of the energy; and the same for 1 s windows against 2 to 6 s either side, for events of
           a few seconds: an event a listener would hear come round every 30 s              at most STAND_DB

Cues (mono): peak (under -3 dBFS), seconds (CUE_SECONDS), and the ends: `edges` is the loudest sample in the
first and last 5 ms, dB below the cue's own peak (at least EDGE_DB below: no click). `loud` is the cue's
loudest 100 ms (RMS, dBFS); the build prints `over`, that plus the cue's level minus the bed's RMS: how far the
cue rises above the bed where it is loudest when an app plays both at their levels (no limit; see README).
After encoding, the decoded length must be the source's and the decoded RMS above -70 dBFS (not silence).
"""
import math

from .core import BED_PEAK_DB, BED_RMS_DB, BED_RMS_TOLERANCE, CUE_PEAK_DB, CUE_SECONDS, RATE, db, looping
from .filters import highpass, highshelf, lowpass

SPREAD_DB = 10.0
STAND_DB = 4.0
EDGE_DB = 40.0
WINDOW = 0.25
BANDS = (("<250", None, 250.0), ("250-2k", 250.0, 2000.0), ("2k-8k", 2000.0, 8000.0), (">8k", 8000.0, None))


def _percentile(values, q):
    s = sorted(values)
    return s[min(len(s) - 1, int(q * len(s)))] if s else 0.0


def _windows_db(x, size):
    out = []
    for i in range(0, len(x) - size + 1, size):
        seg = x[i:i + size]
        out.append(db(math.sqrt(sum(v * v for v in seg) / size)))
    return out


def _stand(w, near=2, far=8):
    """The most one window rises above the median of its neighbourhood (`near` to `far` windows away), around
    the loop."""
    m = len(w)
    worst = -100.0
    offsets = list(range(-far, -near + 1)) + list(range(near, far + 1))
    for i in range(m):
        around = sorted(w[(i + d) % m] for d in offsets)
        worst = max(worst, w[i] - around[len(around) // 2])
    return worst


def _stands(x, size):
    """_stand at two scales: 250 ms windows against 0.5 to 2 s around, and 1 s windows (four of the small ones
    averaged in power) against 2 to 6 s around, which is what catches an event of two or three seconds."""
    small = _windows_db(x, size)
    power = [10 ** (v / 10) for v in small]
    big = [10 * math.log10(max(1e-20, sum(power[(i + d) % len(power)] for d in range(4)) / 4)) for i in range(len(power))]
    return max(_stand(small), _stand(big, 8, 24))


def seam(x, around=2400):
    """(step, slope) across the wrap of a loop: the step from the last sample to the first, and the larger
    second difference there (a kink), each over four times the RMS of the same quantity in the `around`
    samples either side of the seam (50 ms). At most 1.0 means the seam moves no more than the file does
    there; a perfect loop gives about 0.25 on average and over 1.0 about once in 15000."""
    n = len(x)
    idx = [i % n for i in range(-around, around)]
    steps = [x[(i + 1) % n] - x[i] for i in idx if i != n - 1]
    kinks = [x[(i + 1) % n] - 2 * x[i] + x[i - 1] for i in idx if i not in (n - 1, 0)]
    s_step = 4 * math.sqrt(sum(v * v for v in steps) / len(steps)) or 1e-12
    s_kink = 4 * math.sqrt(sum(v * v for v in kinks) / len(kinks)) or 1e-12
    step = abs(x[0] - x[-1])
    kink = max(abs(x[0] - 2 * x[-1] + x[-2]), abs(x[1] - 2 * x[0] + x[-1]))
    return step / s_step, kink / s_kink


def bed_rms(left, right):
    """The RMS of both channels together, dBFS."""
    return db(math.sqrt((sum(v * v for v in left) + sum(v * v for v in right)) / (2 * len(left))))


def bed(left, right):
    """The measures of a stereo bed, as a dict."""
    n = len(left)
    power = (sum(v * v for v in left) + sum(v * v for v in right)) / (2 * n)
    peak = max(max(abs(v) for v in left), max(abs(v) for v in right))
    dc = max(abs(sum(left) / n), abs(sum(right) / n))
    sl = sum(v * v for v in left)
    sr = sum(v * v for v in right)
    corr = sum(a * b for a, b in zip(left, right)) / math.sqrt(sl * sr) if sl > 0 and sr > 0 else 1.0
    sL, kL = seam(left)
    sR, kR = seam(right)
    mid = [(a + b) * 0.5 for a, b in zip(left, right)]
    size = int(WINDOW * RATE)
    whole = _windows_db(mid, size)
    spread = max(whole) - sorted(whole)[len(whole) // 2]
    stands = {"all": _stands(mid, size)}
    energies = {}
    with looping():
        lo = lowpass(mid, 250.0)
        b2 = lowpass(highpass(mid, 250.0), 2000.0)
        b3 = lowpass(highpass(mid, 2000.0), 8000.0)
        hi = highpass(mid, 8000.0)
        kl = highshelf(highpass(left, 38.0, 0.5), 1500.0, 4.0)
        kr = highshelf(highpass(right, 38.0, 0.5), 1500.0, 4.0)
    loudness = -0.691 + 10 * math.log10(max(1e-20, (sum(v * v for v in kl) + sum(v * v for v in kr)) / n))
    signals = dict(zip((b[0] for b in BANDS), (lo, b2, b3, hi)))
    for name, sig in signals.items():
        energies[name] = sum(v * v for v in sig)
    total = sum(energies.values()) or 1.0
    shares = {k: v / total for k, v in energies.items()}
    for name, sig in signals.items():
        if shares[name] >= 0.05:
            stands[name] = _stands(sig, size)
    return {
        "seconds": n / RATE,
        "peak": db(peak),
        "rms": db(math.sqrt(power)),
        "lufs": loudness,
        "dc": db(dc),
        "corr": corr,
        "seam": max(sL, sR),
        "slope": max(kL, kR),
        "bands": {k: round(100 * v, 1) for k, v in shares.items()},
        "spread": spread,
        "stand": max(stands.values()),
        "standBand": max(stands, key=stands.get),
    }


def bed_faults(m):
    f = []
    if m["peak"] >= BED_PEAK_DB:
        f.append("peak %.1f dBFS, at or over %.0f" % (m["peak"], BED_PEAK_DB))
    if abs(m["rms"] - BED_RMS_DB) > BED_RMS_TOLERANCE:
        f.append("rms %.1f dBFS, more than %.0f dB from %.0f" % (m["rms"], BED_RMS_TOLERANCE, BED_RMS_DB))
    if m["dc"] > -50:
        f.append("dc offset %.0f dBFS" % m["dc"])
    if not 0.05 <= m["corr"] <= 0.90:
        f.append("left/right correlation %.2f, outside 0.05..0.90" % m["corr"])
    if m["seam"] > 1.0 or m["slope"] > 1.0:
        f.append("the loop seam moves more than the file does (step %.2f, slope %.2f)" % (m["seam"], m["slope"]))
    if m["spread"] > SPREAD_DB:
        f.append("its loudest moment is %.1f dB over the median, more than %.0f" % (m["spread"], SPREAD_DB))
    if m["stand"] > STAND_DB:
        f.append("one moment stands %.1f dB out of its surroundings (%s), more than %.0f: an event belongs in a cue"
                 % (m["stand"], m["standBand"], STAND_DB))
    if abs(m["seconds"] - round(m["seconds"])) > 1e-6:
        f.append("%.4f s long" % m["seconds"])
    return f


def cue(x):
    n = len(x)
    peak = max((abs(v) for v in x), default=0.0)
    e = int(0.005 * RATE)
    head = max((abs(v) for v in x[:e]), default=0.0)
    tail = max((abs(v) for v in x[-e:]), default=0.0)
    w, hop = int(0.1 * RATE), int(0.025 * RATE)
    loud = max((sum(v * v for v in x[i:i + w]) / w for i in range(0, max(1, n - w + 1), hop)), default=0.0)
    return {
        "seconds": n / RATE,
        "peak": db(peak),
        "rms": db(math.sqrt(sum(v * v for v in x) / n)) if n else -200.0,
        "loud": db(math.sqrt(loud)),
        "edges": db(peak) - db(max(head, tail)),
    }


def cue_faults(m):
    f = []
    if m["peak"] >= BED_PEAK_DB:
        f.append("peak %.1f dBFS, at or over %.0f" % (m["peak"], BED_PEAK_DB))
    if not CUE_SECONDS[0] <= m["seconds"] <= CUE_SECONDS[1]:
        f.append("%.2f s long, outside %.1f..%.1f" % (m["seconds"], CUE_SECONDS[0], CUE_SECONDS[1]))
    if m["edges"] < EDGE_DB:
        f.append("its ends are only %.0f dB below its peak (it would click)" % m["edges"])
    if m["rms"] < -70:
        f.append("silent (rms %.0f dBFS)" % m["rms"])
    return f
