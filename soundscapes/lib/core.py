"""The fixed facts every soundscape shares, the loop mode, and the Studio a recipe is handed.

Loop mode. A bed is a loop: every filter in it runs around the circle (its state at the first sample is what it
would be after the last), and every event placed near the end wraps round to the start. A cue is a one-shot:
filters start from rest and an event past the end is cut. The build sets the mode before it calls a recipe
(`looping()` around `day`/`night`, `one_shot()` around `cues`), and every toolkit function that cares reads it, so
a recipe never passes it. A function that takes `loop=None` can be forced either way by passing True or False.
"""
import contextlib, math, random, zlib

RATE = 48_000              # every file, bed and cue
BED_SECONDS = 30           # a bed's length; a loop of exactly RATE * BED_SECONDS frames
BED_RMS_DB = -26.0         # every bed is normalised to this RMS (the mean of both channels), within BED_RMS_TOLERANCE
BED_RMS_TOLERANCE = 1.0    # dB
BED_PEAK_DB = -3.0         # no bed sample reaches this
CUE_LOUD_DB = -20.0        # every cue file is normalised so its loudest 100 ms has this RMS: 6 dB over a bed's RMS
CUE_PEAK_DB = -7.0         # and a sharper peak than that allows is bent under this by the soft limiter
CUE_SECONDS = (0.2, 4.0)   # the shortest and longest cue
CONTROL_RATE = 100         # points a second in a control curve (lib.control)

_state = {"loop": False}


def is_looping(loop=None):
    """The mode a function should use: `loop` when given, else the build's current one."""
    return _state["loop"] if loop is None else bool(loop)


@contextlib.contextmanager
def looping():
    old, _state["loop"] = _state["loop"], True
    try:
        yield
    finally:
        _state["loop"] = old


@contextlib.contextmanager
def one_shot():
    old, _state["loop"] = _state["loop"], False
    try:
        yield
    finally:
        _state["loop"] = old


def seed(*parts):
    """A fixed seed from names: the same names give the same seed on every machine."""
    return zlib.crc32("/".join(str(p) for p in parts).encode("utf-8"))


def db(x):
    """Amplitude to dB (full scale is 0 dB); silence is -200."""
    return 20 * math.log10(x) if x > 1e-10 else -200.0


def undb(d):
    """dB to amplitude."""
    return 10 ** (d / 20)


def samples(seconds):
    """Seconds to a whole number of samples at RATE."""
    return int(round(seconds * RATE))


class Studio:
    """What a recipe's `day(s)`, `night(s)` and `cues(s)` are given.

    s.biome    the biome id ("forest")
    s.part     "day", "night" or "cues"
    s.rate     RATE
    s.seconds  the bed's length in seconds (BED_SECONDS)
    s.n        the bed's length in samples; `day` and `night` return two lists of exactly this many floats
    s.rng(name)  a random.Random seeded from (biome, part, name): one per layer, so changing one layer's draws
                 leaves the others' alone
    """

    def __init__(self, biome, part):
        self.biome, self.part = biome, part
        self.rate, self.seconds = RATE, BED_SECONDS
        self.n = RATE * BED_SECONDS

    def rng(self, name):
        return random.Random(seed(self.biome, self.part, name))


class Cue:
    """One cue as a recipe hands it over (lib.cue builds one). `beds` names the beds it is scattered over,
    `every` is [min, max] seconds between two of it, `level` the dB to play the file at over a bed played at 0
    dB, `spread` how far from the centre it may be panned (0 centre only, 1 anywhere)."""

    def __init__(self, id, samples, beds, every, level, spread):
        self.id, self.samples, self.beds = id, samples, tuple(beds)
        self.every, self.level, self.spread = (float(every[0]), float(every[1])), float(level), float(spread)


def cue(id, samples, beds=("day",), every=(20, 60), level=-3.0, spread=0.6):
    """A cue for `cues(s)` to return: an id (lower-case words and hyphens; the file is cues/<biome>-<id>.ogg),
    the mono samples (any level: the build trims the silence, fades the ends and sets the loudness), the beds
    it plays over ("day", "night" or both), how often ([min, max] seconds between two), its level (dB of gain
    an app plays the file at, over a bed played at 0: every file's loudest 100 ms is 6 dB over a bed's RMS,
    so level -6 brings the cue's loudest moment level with the bed, 0 puts it 6 dB above), and its stereo
    spread (0..1)."""
    return Cue(id, samples, beds, every, level, spread)
