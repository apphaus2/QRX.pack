"""Original demo assets for QRX.pack: a test card PNG and two short sounds. Pure standard library."""
import math, struct, sys, wave, zlib, random

out = sys.argv[1]

def png(path, w, h, pixel):
    rows = b"".join(b"\x00" + bytes(c for x in range(w) for c in pixel(x, y)) for y in range(h))
    def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    data = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b"")
    open(path, "wb").write(data)

BARS = [(235, 235, 235), (240, 200, 40), (40, 190, 210), (60, 180, 75), (200, 60, 190), (220, 50, 50), (40, 70, 200)]
def card(x, y, n=512):
    cx, cy = x - n / 2, y - n / 2
    r = math.hypot(cx, cy)
    if abs(r - 180) < 6: return (255, 255, 255)            # ring
    if r < 180 and (abs(cx) < 3 or abs(cy) < 3): return (255, 255, 255)  # crosshair
    if y < n * 0.62: return BARS[min(6, x * 7 // n)]       # colour bars
    if y < n * 0.70: return BARS[6 - min(6, x * 7 // n)] if (x // 32) % 2 else (20, 20, 20)
    g = int(255 * x / (n - 1))                              # grey ramp
    return (g, g, g)
png(f"{out}/images/test-card.png", 512, 512, card)

RATE = 22050
def wav(path, samples):
    with wave.open(path, "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(RATE)
        f.writeframes(b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 30000)) for s in samples))

def tone(freq, dur, vib=0.0, harmonics=(1, 0.35, 0.15)):
    n = int(RATE * dur)
    for i in range(n):
        t = i / RATE
        env = min(1, t / 0.04) * min(1, (dur - t) / 0.12)
        f = freq * (1 + vib * math.sin(2 * math.pi * 5.5 * t))
        yield env * sum(a * math.sin(2 * math.pi * f * (k + 1) * t) for k, a in enumerate(harmonics)) / 1.5

# The bush's song: a short pentatonic tune with a little vibrato.
notes = [(392, .4), (440, .4), (523, .6), (440, .3), (392, .3), (330, .8), (392, .4), (523, .4), (587, .9)]
song = [s for f, d in notes for s in tone(f, d, vib=0.006)]
wav(f"{out}/sounds/song.wav", [s * 0.8 for s in song])

# The fox's yip: two quick rising chirps with a breathy edge.
random.seed(7)
def chirp(dur=0.16, f0=650, f1=1300):
    n = int(RATE * dur); phase = 0
    for i in range(n):
        t = i / RATE; f = f0 + (f1 - f0) * (t / dur) ** 0.6; phase += 2 * math.pi * f / RATE
        env = math.sin(math.pi * t / dur) ** 1.5
        yield env * (0.8 * math.sin(phase) + 0.25 * math.sin(2 * phase) + 0.08 * (random.random() * 2 - 1))
wav(f"{out}/sounds/yip.wav", list(chirp()) + [0.0] * int(RATE * 0.07) + list(chirp(0.13, 700, 1450)))
