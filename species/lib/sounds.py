"""The creatures' voices: short synthesized sounds written as WAV files (standard library only, nothing sampled),
after the yip and the song in QRX.pack's scripts/assets.py.

A voice (sounds.json) gives a sound for each meaning (`call`, `content`, `alarm`, `curious`), each a `kind` from
KINDS below with a `pitch` and a `length` (multipliers) and a `gain`. A kind is a few tones and puffs of noise in a
row. Everything is 16-bit mono at the rate in sounds.json, quiet, and starts and ends at silence; the noise comes
from a seeded generator, so the same voice writes the same bytes.
"""
import math, random, struct, zlib

PEAK = 0.28            # of full scale: these play close to the ear, on top of whatever else the room is doing


def _tone(rate, f0, f1, seconds, harmonics=((1, 1.0),), attack=0.008, release=0.03, tremolo=(0.0, 0.0), swell=False, breath=0.0, rng=None, curve=0.6):
    """A tone sliding from f0 to f1 Hz: `harmonics` are (multiple, level), `tremolo` (Hz, depth), `breath` noise."""
    count, out, phase = max(2, int(rate * seconds)), [], 0.0
    top = 0.45 * rate
    for i in range(count):
        t = i / rate
        f = min(top, f0 + (f1 - f0) * (t / seconds) ** curve)
        phase += 2 * math.pi * f / rate
        env = math.sin(math.pi * t / seconds) if swell else min(1.0, t / attack) * min(1.0, (seconds - t) / release)
        if tremolo[0]: env *= 1 - tremolo[1] * (0.5 + 0.5 * math.sin(2 * math.pi * tremolo[0] * t))
        value = sum(level * math.sin(phase * k) for k, level in harmonics if f * k < top)
        if breath: value += breath * (rng.random() * 2 - 1)
        out.append(env * value)
    return out


def _noise(rate, seconds, rng, smooth=0.3, bright=False, swell=True, attack=0.01, release=0.03):
    """Noise through a one-pole low-pass (`smooth` nearer 0 is duller); `bright` keeps what the filter removes."""
    count, out, low = max(2, int(rate * seconds)), [], 0.0
    for i in range(count):
        t = i / rate
        white = rng.random() * 2 - 1
        low += smooth * (white - low)
        env = math.sin(math.pi * t / seconds) if swell else min(1.0, t / attack) * min(1.0, (seconds - t) / release)
        out.append(env * ((white - low) if bright else low))
    return out


def _gap(rate, seconds): return [0.0] * int(rate * seconds)


def _kind(kind, rate, p, n, rng):
    """The samples of one kind at pitch `p` and length `n`."""
    if kind == "chirp": return _tone(rate, 2400 * p, 3900 * p, 0.07 * n) + _gap(rate, 0.04 * n) + _tone(rate, 2600 * p, 4200 * p, 0.06 * n)
    if kind == "peep": return _tone(rate, 2500 * p, 3900 * p, 0.11 * n, curve=1.4)
    if kind == "trill":
        out = []
        for k in range(7): out += _tone(rate, (2900 + 90 * k) * p, (3400 + 90 * k) * p, 0.035 * n, release=0.012) + _gap(rate, 0.022 * n)
        return out
    if kind == "squeak": return _tone(rate, 3000 * p, 4400 * p, 0.05 * n, release=0.005) + _tone(rate, 4400 * p, 3500 * p, 0.06 * n, attack=0.003)
    if kind == "hoot": return _tone(rate, 390 * p, 350 * p, 0.20 * n, ((1, 1.0), (2, 0.2)), attack=0.03, release=0.06) + _gap(rate, 0.09 * n) + _tone(rate, 370 * p, 330 * p, 0.30 * n, ((1, 1.0), (2, 0.2)), attack=0.03, release=0.1)
    if kind == "coo": return _tone(rate, 470 * p, 410 * p, 0.42 * n, ((1, 1.0), (2, 0.3)), attack=0.04, release=0.1, tremolo=(14.0, 0.35))
    if kind == "caw": return _tone(rate, 820 * p, 620 * p, 0.26 * n, ((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.35)), attack=0.01, release=0.06, tremolo=(70.0, 0.5), breath=0.1, rng=rng)
    if kind == "yip": return _tone(rate, 700 * p, 1400 * p, 0.12 * n, ((1, 1.0), (2, 0.3), (3, 0.1)), swell=True, breath=0.06, rng=rng)
    if kind == "thump": return _tone(rate, 120 * p, 55 * p, 0.13 * n, attack=0.004, release=0.1) + _gap(rate, 0.08 * n) + _tone(rate, 110 * p, 50 * p, 0.13 * n, attack=0.004, release=0.1)
    if kind == "croak": return _tone(rate, 190 * p, 160 * p, 0.30 * n, ((1, 1.0), (2, 0.6), (3, 0.4), (4, 0.3)), attack=0.02, release=0.05, tremolo=(42.0, 0.9))
    if kind == "buzz": return _tone(rate, 230 * p, 210 * p, 0.32 * n, ((1, 1.0), (2, 0.8), (3, 0.6), (4, 0.45), (5, 0.3)), attack=0.03, release=0.06, tremolo=(28.0, 0.4))
    if kind == "purr": return _tone(rate, 95 * p, 90 * p, 0.55 * n, ((1, 1.0), (2, 0.7), (3, 0.5), (4, 0.3)), swell=True, tremolo=(24.0, 0.8))
    if kind == "hum": return _tone(rate, 150 * p, 150 * p, 0.45 * n, ((1, 1.0), (2, 0.5), (3, 0.25)), swell=True)
    if kind == "bubble":
        out = []
        for k in range(3): out += _tone(rate, (380 + 120 * k) * p, (800 + 150 * k) * p, 0.045 * n, swell=True) + _gap(rate, 0.05 * n)
        return out
    if kind == "click":
        out = []
        for k in range(3): out += _tone(rate, 2600 * p, 2300 * p, 0.014, attack=0.001, release=0.012, breath=0.3, rng=rng) + _gap(rate, 0.05 * n)
        return out
    if kind == "puff":
        out = []
        for k in range(3): out += _noise(rate, 0.05 * n, rng, min(0.9, 0.25 * p)) + _gap(rate, 0.05 * n)
        return out
    if kind == "hiss": return _noise(rate, 0.32 * n, rng, min(0.9, 0.5 / p), bright=True)
    if kind == "whoosh": return _noise(rate, 0.42 * n, rng, min(0.9, 0.08 * p))
    raise KeyError(kind)


KINDS = ("chirp", "peep", "trill", "squeak", "hoot", "coo", "caw", "yip", "thump", "croak", "buzz", "purr", "hum", "bubble", "click", "puff", "hiss", "whoosh")


def synthesize(spec, rate, pitch=1.0, length=1.0):
    """The WAV bytes of one sound: `spec` is {"kind", "pitch", "length", "gain"}; `pitch` and `length` multiply its own."""
    p, n = spec.get("pitch", 1.0) * pitch, spec.get("length", 1.0) * length
    rng = random.Random(zlib.crc32(("%s %.4f %.4f" % (spec["kind"], p, n)).encode()))
    samples = _kind(spec["kind"], rate, p, n, rng)
    while len(samples) > 2 and abs(samples[-1]) < 1e-9 and abs(samples[-2]) < 1e-9: samples.pop()      # no silence at the end
    loudest = max(abs(s) for s in samples) or 1.0
    scale = PEAK * spec.get("gain", 1.0) * 32767 / loudest
    data = struct.pack("<%dh" % len(samples), *(int(round(s * scale)) for s in samples))
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(data)) + data)


def file_name(voice, meaning, pitch, length):
    """What a sound is called on disk: the voice, the meaning, and the rarity's variation when it has one."""
    plain = abs(pitch - 1) < 1e-9 and abs(length - 1) < 1e-9
    return "%s-%s%s.wav" % (voice, meaning, "" if plain else "-%03d-%03d" % (round(pitch * 100), round(length * 100)))


def resolve(voices, voice):
    """{meaning: spec} for a voice, with a meaning that borrows another's ("curious": "call") followed."""
    entry, out = voices[voice], {}
    for meaning, spec in entry.items():
        hops = 0
        while isinstance(spec, str) and hops < 4: meaning_from, spec, hops = spec, entry.get(spec), hops + 1
        out[meaning] = spec
    return out


def source(voices, voice, meaning):
    """The meaning whose file `meaning` plays: itself, or the one it borrows."""
    spec, hops = voices[voice].get(meaning), 0
    while isinstance(spec, str) and hops < 4: meaning, spec, hops = spec, voices[voice].get(spec), hops + 1
    return meaning


def inspect(data, rate, limits):
    """(faults, facts) for a WAV file on disk."""
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:16] != b"WAVEfmt ": return ["not a WAV file"], {}
    size, kind, channels, file_rate, _, _, bits = struct.unpack_from("<IHHIIHH", data, 16)
    faults = []
    if struct.unpack_from("<I", data, 4)[0] != len(data) - 8: faults.append("the RIFF length is not the file's")
    if (size, kind, channels, bits) != (16, 1, 1, 16) or file_rate != rate: faults.append("not 16-bit mono PCM at %d Hz" % rate)
    if data[36:40] != b"data" or struct.unpack_from("<I", data, 40)[0] != len(data) - 44 or (len(data) - 44) % 2: return faults + ["the data chunk is not the rest of the file"], {}
    samples = struct.unpack_from("<%dh" % ((len(data) - 44) // 2), data, 44)
    seconds, peak = len(samples) / rate, max(abs(s) for s in samples) / 32767 if samples else 0.0
    if len(data) > limits["file"]: faults.append("%d bytes, over the %d allowed" % (len(data), limits["file"]))
    if not 0.03 <= seconds <= limits["seconds"]: faults.append("%.2f s long; a sound is 0.03 to %.1f s" % (seconds, limits["seconds"]))
    if not 0.05 <= peak <= PEAK + 0.01: faults.append("its peak is %.2f of full scale; quiet is 0.05 to %.2f" % (peak, PEAK))
    if samples and (abs(samples[0]) > 1500 or abs(samples[-1]) > 1500): faults.append("it does not start and end at silence, so it would click")
    return faults, {"bytes": len(data), "seconds": round(seconds, 3), "peak": round(peak, 3)}
