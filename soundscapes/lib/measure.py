"""Numbers that stand in for ears: what the build prints after every file and what `--check` holds them to.

Beds (stereo, measured on the decoded file):
  peak     the highest sample, dBFS                          under BED_PEAK_DB (-3)
  rms      the mean power of both channels, dBFS (no limit since 2026-11-14: beds are set by loudness)
  dc       the larger channel mean, dBFS                     under -50
  corr     left/right correlation                            0.05 to 0.90: not mono, not anti-phase
  seam     the step across the wrap (last sample to first) over four times the RMS of the sample-to-sample
           steps in the 50 ms either side of it, the larger of the two channels; and `slope`, the same for the
           second difference (a kink)                       each at most 1.0: the seam moves no more than the
                                                             file's own ordinary movement there
  lufs     loudness after the K-weighting of ITU-R BS.1770 (a high-pass at 38 Hz, +4 dB above 1.5 kHz), ungated:
           how loud the bed sounds, where rms is how much energy it has  within BED_LUFS_TOLERANCE of BED_LUFS
                                                                        (-24 +- 1)
  bands    share of the energy below 250 Hz, 250 Hz-2 kHz, 2-8 kHz and above 8 kHz (a fingerprint)
  >2k, >8k the shares above 2 kHz (2-8k plus >8k) and above 8 kHz   at most BRIGHTNESS[part] (day 25 and 4,
                                                                    night 40 and 4)
  spread   the loudest 250 ms window over the median window, dB (of the whole signal)      at most SPREAD_DB
  stand    the largest amount by which one 250 ms window rises above its surroundings (the median of the
           windows 0.5 to 2 s either side, around the loop), dB, over the whole signal and each band holding
           5% or more of the energy; and the same for 1 s windows against 2 to 6 s either side, for events of
           a few seconds: an event a listener would hear come round every 30 s              at most STAND_DB

Cues (mono): peak (under -3 dBFS), seconds (CUE_SECONDS), and the ends: `edges` is the loudest sample in the
first and last 5 ms, dB below the cue's own peak (at least EDGE_DB below: no click). `loud` is the cue's
loudest 100 ms (RMS, dBFS); the build prints `over`, that plus the cue's level minus its bed's RMS: how far the
cue rises above the bed where it is loudest when an app plays both at their levels (no limit; see README).
`snap` is the loudest 5 ms over the loudest 100 ms, dB: high for a knock, a snap or a click.
Schedule (`schedule_faults`, per bed): no cue's `every` minimum under CUE_EVERY_MIN (60 s); at most one near cue
(level above CUE_NEAR_LEVEL, -4), and no near cue with a snap over CUE_SHARP_DB (6 dB). `per_minute` is a bed's
expected events a minute (each cue once per mean of its `every`); printed, aim at about one or fewer.
After encoding, the decoded length must be the source's and the decoded RMS above -70 dBFS (not silence).
"""
import math

from .core import (BED_LUFS, BED_LUFS_TOLERANCE, BED_PEAK_DB, BRIGHTNESS, CUE_EVERY_MIN, CUE_NEAR_LEVEL,
                   CUE_SECONDS, CUE_SHARP_DB, RATE, db, looping)
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


def loudness(left, right):
    """Ungated K-weighted loudness of a stereo loop (BS.1770's filters, run around the loop), LUFS."""
    with looping():
        kl = highshelf(highpass(left, 38.0, 0.5), 1500.0, 4.0)
        kr = highshelf(highpass(right, 38.0, 0.5), 1500.0, 4.0)
    return -0.691 + 10 * math.log10(max(1e-20, (sum(v * v for v in kl) + sum(v * v for v in kr)) / len(left)))


def band_signals(mid):
    """The four bands of a mono loop, in BANDS' order."""
    with looping():
        return (lowpass(mid, 250.0), lowpass(highpass(mid, 250.0), 2000.0),
                lowpass(highpass(mid, 2000.0), 8000.0), highpass(mid, 8000.0))


def shares(signals):
    """Each band's share of the four bands' energy (0..1), by name."""
    energies = {b[0]: sum(v * v for v in sig) for b, sig in zip(BANDS, signals)}
    total = sum(energies.values()) or 1.0
    return {k: v / total for k, v in energies.items()}


def brightness(bands):
    """(percent above 2 kHz, percent above 8 kHz) from a `bands` dict in percent."""
    return bands["2k-8k"] + bands[">8k"], bands[">8k"]


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
    sigs = band_signals(mid)
    share = shares(sigs)
    signals = dict(zip((b[0] for b in BANDS), sigs))
    for name, sig in signals.items():
        if share[name] >= 0.05:
            stands[name] = _stands(sig, size)
    return {
        "seconds": n / RATE,
        "peak": db(peak),
        "rms": db(math.sqrt(power)),
        "lufs": loudness(left, right),
        "dc": db(dc),
        "corr": corr,
        "seam": max(sL, sR),
        "slope": max(kL, kR),
        "bands": {k: round(100 * v, 1) for k, v in share.items()},
        "spread": spread,
        "stand": max(stands.values()),
        "standBand": max(stands, key=stands.get),
    }


def bed_faults(m, part):
    f = []
    if m["peak"] >= BED_PEAK_DB:
        f.append("peak %.1f dBFS, at or over %.0f" % (m["peak"], BED_PEAK_DB))
    if abs(m["lufs"] - BED_LUFS) > BED_LUFS_TOLERANCE:
        f.append("loudness %.1f LUFS, more than %.0f dB from %.0f" % (m["lufs"], BED_LUFS_TOLERANCE, BED_LUFS))
    above2, above8 = brightness(m["bands"])
    top2, top8 = BRIGHTNESS[part]
    if above2 > top2 or above8 > top8:
        f.append("too bright for a %s bed: %.1f%% of its energy above 2 kHz and %.1f%% above 8 kHz (at most %.0f and %.0f)"
                 % (part, above2, above8, top2, top8))
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
    w5 = int(0.005 * RATE)
    loud5 = max((sum(v * v for v in x[i:i + w5]) / w5 for i in range(0, max(1, n - w5 + 1), w5 // 4)), default=0.0)
    return {
        "snap": db(math.sqrt(loud5)) - db(math.sqrt(loud)),
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


def per_minute(cues, part):
    """Expected events a minute over one bed: each cue once per mean of its `every`."""
    return sum(120.0 / (c["every"][0] + c["every"][1]) for c in cues if part in c["beds"])


def schedule_faults(cues, part):
    """Faults in how one bed's cues are spaced and placed. `cues` are index entries, each with the cue's measured
    `snap` added."""
    f = []
    mine = [c for c in cues if part in c["beds"]]
    for c in mine:
        if c["every"][0] < CUE_EVERY_MIN:
            f.append("cue %s comes round every %.0f s at the least; no cue more often than once in %.0f s"
                     % (c["id"], c["every"][0], CUE_EVERY_MIN))
    near = [c for c in mine if c["level"] > CUE_NEAR_LEVEL]
    if len(near) > 1:
        f.append("the %s bed has %d near cues (level above %.0f: %s); one hero at most, the rest far off"
                 % (part, len(near), CUE_NEAR_LEVEL, ", ".join(c["id"] for c in near)))
    for c in near:
        if c.get("snap") is not None and c["snap"] > CUE_SHARP_DB:
            f.append("cue %s is sharp (snap %.1f dB) and near (level %.0f): a sharp sound must be far off (level "
                     "%.0f or lower)" % (c["id"], c["snap"], c["level"], CUE_NEAR_LEVEL))
    return f
