"""Voices for cues (and grains for scatter): short mono sounds made of tones, noise and resonances.

Everything here returns a mono list at RATE starting and ending at silence, at no particular level (the build
normalises a finished cue's peak). Combine them with `seq` (one after another), `overlay` (one on another at a
time), `distant` (further away) and `space` (in the open air, with a tail).

Frequencies are Hz and times seconds. Where a function takes `rng`, it draws its small variations from it; pass
the cue's own rng so a cue is the same on every build.
"""
import math

from .core import RATE, one_shot, undb
from .filters import bandpass, highpass, lowpass, onepole_lowpass

TAU = 2 * math.pi


def silence(seconds):
    return [0.0] * max(0, int(round(seconds * RATE)))


def envelope(seconds, attack=0.01, release=0.05, curve=1.0):
    """1 in the middle, rising over `attack` and falling over `release` (half-cosine shoulders); `curve` above 1
    makes the release fall away faster at first, as a struck or plucked thing does."""
    n = max(2, int(round(seconds * RATE)))
    a, r = max(1, int(attack * RATE)), max(1, int(release * RATE))
    out = []
    for i in range(n):
        g = 1.0
        if i < a:
            g = 0.5 * (1 - math.cos(math.pi * i / a))
        tail = n - 1 - i
        if tail < r:
            q = tail / r
            g *= (0.5 * (1 - math.cos(math.pi * q))) ** curve
        out.append(g)
    return out


def decay(seconds, tau, attack=0.002):
    """An exponential decay with time constant `tau`, a short attack, and a fade over the last 10% so it ends
    at zero."""
    n = max(2, int(round(seconds * RATE)))
    a = max(1, int(attack * RATE))
    f = max(1, n // 10)
    out = []
    for i in range(n):
        g = math.exp(-i / (tau * RATE))
        if i < a:
            g *= i / a
        if n - 1 - i < f:
            g *= (n - 1 - i) / f
        out.append(g)
    return out


def _contour(hz, seconds):
    """A frequency at every sample: `hz` is a number, (from, to), or [(share of the length, Hz), ...]
    interpolated in log frequency."""
    n = max(2, int(round(seconds * RATE)))
    if isinstance(hz, (int, float)):
        return [float(hz)] * n
    if len(hz) == 2 and all(isinstance(v, (int, float)) for v in hz):
        hz = [(0.0, hz[0]), (1.0, hz[1])]
    pts = sorted(hz)
    out, k = [], 0
    for i in range(n):
        u = i / (n - 1)
        while k < len(pts) - 2 and u > pts[k + 1][0]:
            k += 1
        (u0, f0), (u1, f1) = pts[k], pts[min(k + 1, len(pts) - 1)]
        w = 0.0 if u1 <= u0 else min(1.0, max(0.0, (u - u0) / (u1 - u0)))
        out.append(math.exp(math.log(f0) + (math.log(f1) - math.log(f0)) * w))
    return out


def tone(seconds, hz, harmonics=((1, 1.0),), attack=0.01, release=0.05, curve=1.0, vibrato=(0.0, 0.0),
         tremolo=(0.0, 0.0), breath=0.0, rng=None):
    """A voiced tone. `hz` is a number, (from, to) for a glide, or a contour [(share, Hz), ...].
    `harmonics` are (multiple, level); `vibrato` is (Hz, depth as a share of the pitch), `tremolo` (Hz, depth
    0..1); `breath` mixes in that much noise, shaped by the same envelope (needs rng)."""
    freqs = _contour(hz, seconds)
    env = envelope(seconds, attack, release, curve)
    top = 0.45 * RATE
    vr, vd = vibrato
    tr, td = tremolo
    out, phase = [], 0.0
    for i, (f, e) in enumerate(zip(freqs, env)):
        t = i / RATE
        if vd:
            f *= 1 + vd * math.sin(TAU * vr * t)
        phase += TAU * f / RATE
        v = 0.0
        for k, level in harmonics:
            if f * k < top:
                v += level * math.sin(phase * k)
        if td:
            e *= 1 - td * (0.5 + 0.5 * math.sin(TAU * tr * t))
        if breath:
            v += breath * (rng.random() * 2 - 1)
        out.append(v * e)
    return out


def noise_burst(rng, seconds, lo=200.0, hi=6000.0, attack=0.005, release=0.05, curve=1.0):
    """A puff of band-limited noise (lo..hi Hz) under an envelope: rustle, breath, splash, a footstep."""
    n = max(2, int(round(seconds * RATE)))
    x = [rng.random() * 2 - 1 for _ in range(n)]
    with one_shot():
        if lo > 20:
            x = highpass(x, lo)
        if hi < 0.45 * RATE:
            x = lowpass(x, hi)
    return [v * e for v, e in zip(x, envelope(seconds, attack, release, curve))]


def knock(rng, hz=900.0, seconds=0.12, q=7.0, body=0.5):
    """One knock on wood: a click of noise ringing in a resonance at `hz` (q: how long it rings) over a short
    low thump (`body`, 0..1)."""
    n = max(2, int(round(seconds * RATE)))
    click = [(rng.random() * 2 - 1) * math.exp(-i / (0.0008 * RATE)) for i in range(n)]
    with one_shot():
        ring = bandpass(click, hz * rng.uniform(0.96, 1.04), q)
        ring2 = bandpass(click, hz * 2.3 * rng.uniform(0.97, 1.03), q * 1.3)
    thump = tone(seconds, (hz * 0.22, hz * 0.17), attack=0.001, release=seconds * 0.8, curve=2.5)
    out = [a + 0.45 * b + body * 0.08 * c for a, b, c in zip(ring, ring2, thump)]
    return [v * e for v, e in zip(out, decay(seconds, seconds / 4, 0.0005))]


def roll(rng, count=14, rate=16.0, hz=950.0, accel=0.0, fade=0.5, seconds_each=0.07):
    """A drum roll of `count` knocks starting at `rate` a second; `accel` > 0 speeds up (the gap shrinks by
    that share over the roll), `fade` is how much quieter the last is than the first (0..1). A woodpecker."""
    gap = 1.0 / rate
    total = gap * count * (1 + abs(accel)) + seconds_each + 0.05
    out = silence(total)
    t = 0.0
    for i in range(count):
        u = i / max(1, count - 1)
        k = knock(rng, hz * rng.uniform(0.98, 1.02), seconds_each, q=9.0, body=0.3)
        g = (1 - fade * u) * rng.uniform(0.85, 1.0)
        overlay(out, k, t, g)
        t += gap * (1 - accel * u)
    return trim(out)


def bell(hz, seconds=2.5, partials=((1.0, 1.0, 1.0), (2.76, 0.45, 0.6), (5.40, 0.2, 0.35), (8.93, 0.1, 0.2)),
         attack=0.003):
    """A struck bell or chime: `partials` are (ratio to hz, level, decay seconds)."""
    n = max(2, int(round(seconds * RATE)))
    out = []
    a = max(1, int(attack * RATE))
    f = max(1, n // 8)
    for i in range(n):
        t = i / RATE
        v = sum(level * math.exp(-t / d) * math.sin(TAU * hz * r * t) for r, level, d in partials if hz * r < 0.45 * RATE)
        g = min(1.0, i / a) * min(1.0, (n - 1 - i) / f)
        out.append(v * g)
    return out


def creak(rng, seconds=1.2, rate=(25.0, 70.0), hz=(420.0, 1100.0), q=6.0):
    """Wood bending: a train of small stick-slip clicks whose rate wanders within `rate` (a second), ringing in
    two resonances drawn from `hz`. A branch, a door, a hull."""
    n = max(2, int(round(seconds * RATE)))
    x = [0.0] * n
    t = 0.0
    r0, r1 = rng.uniform(*rate), rng.uniform(*rate)
    while t < seconds:
        u = t / seconds
        r = r0 + (r1 - r0) * u + rng.uniform(-0.15, 0.15) * r0
        i = int(t * RATE)
        if i < n:
            x[i] += rng.uniform(0.5, 1.0)
        t += 1.0 / max(5.0, r)
    f1, f2 = rng.uniform(*hz), rng.uniform(*hz)
    with one_shot():
        out = [a + 0.6 * b for a, b in zip(bandpass(x, f1, q), bandpass(x, f2 * 1.7, q * 1.2))]
    return [v * e for v, e in zip(out, envelope(seconds, 0.15 * seconds, 0.3 * seconds))]


def snap(rng, seconds=0.35):
    """A twig breaking: three or four sharp crackles within 60 ms, bright and dry, with a little woody ring."""
    out = silence(seconds)
    t = 0.0
    for _ in range(rng.randint(3, 4)):
        c = knock(rng, rng.uniform(1800, 3200), 0.05, q=4.0, body=0.0)
        overlay(out, c, t, rng.uniform(0.5, 1.0))
        t += rng.uniform(0.008, 0.025)
    return trim(out)


def churr(rng, seconds=3.0, hz=1100.0, pulse=(26.0, 30.0), shifts=2):
    """A long mechanical trill: a buzzy tone pulsed `pulse` times a second, the rate and pitch stepping
    `shifts` times along the way. A nightjar, a cicada, some toads."""
    n = max(2, int(round(seconds * RATE)))
    steps = sorted(rng.uniform(0.2, 0.9) for _ in range(shifts))
    out, phase, pp = [], 0.0, 0.0
    env = envelope(seconds, 0.08, 0.3)
    p0, p1 = pulse
    for i in range(n):
        u = i / n
        level = sum(1 for s in steps if u > s)
        f = hz * (1 + 0.07 * level)
        pr = p0 + (p1 - p0) * (level / max(1, shifts))
        phase += TAU * f / RATE
        pp += TAU * pr / RATE
        gate = max(0.0, math.sin(pp)) ** 1.5
        v = math.sin(phase) + 0.35 * math.sin(2 * phase) + 0.15 * math.sin(3 * phase)
        out.append(v * gate * env[i])
    return out


def hoot(hz=380.0, seconds=0.45, fall=0.92, breath=0.08, rng=None):
    """A soft, round hoot falling by `fall` over its length: an owl, a dove, a distant horn."""
    return tone(seconds, [(0.0, hz * 0.97), (0.25, hz), (1.0, hz * fall)], ((1, 1.0), (2, 0.12), (3, 0.04)),
                attack=0.04, release=seconds * 0.45, vibrato=(5.0, 0.004), breath=breath if rng else 0.0, rng=rng)


def caw(rng, hz=620.0, seconds=0.3):
    """A harsh call rich in harmonics with a rough flutter: a crow, a gull, a heron."""
    return tone(seconds, [(0.0, hz * 1.12), (0.3, hz), (1.0, hz * 0.85)],
                ((1, 1.0), (2, 0.8), (3, 0.65), (4, 0.45), (5, 0.3), (6, 0.2)),
                attack=0.015, release=0.08, tremolo=(rng.uniform(55, 75), 0.55), breath=0.15, rng=rng)


def croak(rng, hz=180.0, seconds=0.35, pulse=40.0):
    """A pulsed, nasal call: a frog or a toad. `pulse` is the pulses a second."""
    return tone(seconds, (hz, hz * 0.93), ((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.35), (5, 0.2)),
                attack=0.02, release=0.06, tremolo=(pulse * rng.uniform(0.95, 1.05), 0.9))


def chirp(seconds, hz_from, hz_to, harmonics=((1, 1.0), (2, 0.06))):
    """A quick pure sweep: a bird's note, a bat's call (made audible), a squeak."""
    return tone(seconds, (hz_from, hz_to), harmonics, attack=min(0.006, seconds / 4), release=min(0.02, seconds / 3))


def phrase(rng, notes=6, hz=(2600.0, 5200.0), note=(0.05, 0.14), gap=(0.02, 0.07), shape=None):
    """A songbird's phrase: `notes` short whistled notes, each a rising, falling or bending sweep within `hz`.
    `shape` fixes the melody as [(start Hz, end Hz, seconds), ...] instead; the rng still bends each a little."""
    parts = []
    if shape is None:
        lo, hi = hz
        shape = []
        f = rng.uniform(lo, hi)
        for _ in range(notes):
            g = min(hi, max(lo, f * rng.uniform(0.8, 1.25)))
            shape.append((f, g, rng.uniform(*note)))
            f = min(hi, max(lo, g * rng.uniform(0.85, 1.18)))
    for i, (a, b, d) in enumerate(shape):
        bend = rng.uniform(0.97, 1.03)
        mid = (a * b) ** 0.5 * rng.uniform(0.95, 1.08)
        parts.append(tone(d, [(0.0, a * bend), (0.5, mid), (1.0, b * bend)], ((1, 1.0), (2, 0.05)),
                          attack=min(0.008, d / 4), release=min(0.025, d / 3), vibrato=(rng.uniform(30, 60), 0.01)))
        if i < len(shape) - 1:
            parts.append(silence(rng.uniform(*gap)))
    return seq(*parts)


def trill(rng, count=10, hz=4200.0, each=0.025, gap=0.018, slide=0.0):
    """A run of identical quick notes (`count` of them), the pitch sliding by `slide` (a share) over the run."""
    parts = []
    for i in range(count):
        f = hz * (1 + slide * i / max(1, count - 1)) * rng.uniform(0.99, 1.01)
        parts.append(chirp(each, f * 0.92, f * 1.05))
        parts.append(silence(gap * rng.uniform(0.85, 1.15)))
    return seq(*parts[:-1])


def seq(*parts):
    """Parts one after another."""
    out = []
    for p in parts:
        out.extend(p)
    return out


def overlay(base, x, at, gain=1.0):
    """Adds x into base at `at` seconds, in place, growing base if x runs past its end; returns base."""
    i = int(round(at * RATE))
    need = i + len(x)
    if need > len(base):
        base.extend([0.0] * (need - len(base)))
    base[i:need] = [a + v * gain for a, v in zip(base[i:need], x)]
    return base


def distant(x, amount=0.5):
    """x as if from further off: duller (the highs go first) and softer. amount 0 is here, 1 is far."""
    with one_shot():
        y = lowpass(x, 9000 * (1 - amount) + 1200 * amount)
    return [v * undb(-9 * amount) for v in y]


def space(x, rng, seconds=0.9, wet=0.25, damp=4000.0):
    """x in the open: a short diffuse tail (four damped combs and two all-passes, Schroeder's), `seconds` long,
    mixed in at `wet`. Appends the tail; the end fades to zero."""
    tail = int(seconds * RATE)
    dry = list(x) + [0.0] * tail
    n = len(dry)
    acc = [0.0] * n
    fb = math.exp(math.log(1e-3) * 0.035 / max(0.05, seconds))     # combs about 35 ms long fall 60 dB in `seconds`
    for base in (0.0297, 0.0371, 0.0411, 0.0437):
        d = int(base * rng.uniform(0.95, 1.05) * RATE)
        buf = [0.0] * n
        lp = 0.0
        a = math.exp(-TAU * damp / RATE)
        for i in range(n):
            j = i - d
            back = buf[j] if j >= 0 else 0.0
            lp = a * lp + (1 - a) * back
            buf[i] = dry[i] + fb * lp
        acc = [s + v for s, v in zip(acc, buf)]
    for d, g in ((int(0.005 * RATE), 0.7), (int(0.0017 * RATE), 0.7)):
        out = [0.0] * n
        for i in range(n):
            j = i - d
            out[i] = -g * acc[i] + (acc[j] + g * out[j] if j >= 0 else 0.0)
        acc = out
    peak_dry = max((abs(v) for v in x), default=1.0) or 1.0
    peak_wet = max((abs(v) for v in acc), default=1.0) or 1.0
    k = wet * peak_dry / peak_wet
    mixed = [a + k * b for a, b in zip(dry, acc)]
    f = max(1, int(0.25 * tail))
    for i in range(f):
        mixed[n - 1 - i] *= i / f
    return mixed


def trim(x, floor_db=-60.0):
    """x without the near-silence at either end (below `floor_db` of its peak)."""
    top = max((abs(v) for v in x), default=0.0)
    if top <= 0:
        return list(x)
    t = top * undb(floor_db)
    a = 0
    while a < len(x) and abs(x[a]) < t:
        a += 1
    b = len(x)
    while b > a and abs(x[b - 1]) < t:
        b -= 1
    return list(x[a:b])
