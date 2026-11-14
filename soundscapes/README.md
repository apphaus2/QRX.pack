# Soundscapes

Quiet background sound for each of the 11 biomes in `../species/biomes.json`, for an app to play while a
creature of that biome is out. Per biome there are two beds, `day` and `night` (30 s, stereo, 48 kHz, seamless
loops), and four to six cues per bed (short mono one-shots the app scatters over the bed at random). The format
is Ogg Opus, which SoundLib's soundscape plays.

What they are for (the owner, 2026-11-14, after listening to the first version): ambient sound that breaks up the
silence, not a portrait of a place. A bed is calm, dark and smooth; events are rare, most of them far off; each bed
may have one "hero", the sound that says where you are, a little nearer. The first version's days were harsh and
its cues came every few seconds; the toolkit now holds every bed to a loudness, a brightness ceiling and a cue
spacing, and all eleven are redone to that aim (the forest first, as the model for the other ten).

Everything is synthesized here from noise and tones with fixed seeds. Nothing is recorded or downloaded, so it is
CC0 like the rest of the pack's generated sound. It is stylised on purpose.

Listen to them at **https://qrx-pack.apphaus.us/soundscapes/preview/** (the page in `preview/`, served from this
repository's `master`): pick a biome, Day or Night, and it loops the bed and scatters the cues as an app would.

All eleven biomes are built to the second pass's rules and pass every check: 22 beds, each at -24 LUFS and 40 kbps,
none needing the build's softening, and 97 cues at 0.8 to 1.05 events a minute per bed. The numbers under "Checks" stand in for
ears while a recipe is written: they say a bed is at the right loudness, not too bright, loops without a step, is
not mono and has no single moment that stands out, and that its cues are rare; they do not say it sounds good.
Only listening does.

## Building

```
python3 -I soundscapes/build.py                  # every biome with a recipe, then index.json
python3 -I soundscapes/build.py forest           # one biome: its beds/, cues/ and index/forest.json only
python3 -I soundscapes/build.py forest --wav     # also wav/forest-*.wav (16-bit, the samples before encoding)
python3 -I soundscapes/build.py --index          # index.json from the fragments in index/, nothing built
python3 -I soundscapes/build.py --check          # measure what is on disk; writes nothing; exit 1 on a fault
python3 -I soundscapes/build.py --check forest   # the same for one biome
```

Run from the pack's root with `/usr/bin/python3` (3.9 on this Mac), standard library only, on macOS: encoding and
decoding use `/usr/bin/afconvert`. No numpy, ffmpeg, opusenc or sox.

The forest builds in about 45 s on the owner's Mac (day bed 11 s, night bed 9 s, its eight cues 3 s; the rest is
softening, encoding, decoding and measuring). `--check` of one biome takes about 8 s. Its files total 344 KB:
the beds are 140 and 161, the cues 1 to 10 KB each. `wav/` is ignored by git.

The same recipe gives the same samples on every run (checked: the WAVs from two builds are identical). The Ogg
bytes were identical between two builds here too, but they come from afconvert's encoder, so another macOS version
may write different bytes for the same samples.

### Several authors at once

A recipe file is the only thing a biome's author edits. `build.py <biome> ...` writes only that biome's files:
`beds/<biome>-*.ogg`, `cues/<biome>-*.ogg` (and removes that biome's cues no longer in its recipe), `index/<biome>.json`,
and with `--wav` `wav/<biome>-*.wav`. Each file is written beside its target and moved over it, and temporary files go
in a temporary directory of the process's own, so named builds of different biomes can run at the same time (two
were run side by side and neither touched the other's files or `index.json`). Only `build.py` with no biome named, or
`build.py --index`, writes `index.json`. Do not build the same biome twice at once.

## Layout

```
build.py            the command
lib/                the toolkit (below); a recipe does not change it
recipes/<biome>.py  one recipe per biome; forest.py is the reference
beds/               <biome>-day.ogg, <biome>-night.ogg
cues/               <biome>-<cue>.ogg
index/<biome>.json  what one biome's build wrote: its index entry plus a `build` block (recipe and toolkit hashes,
                    timings, exact frame counts, every measure)
index.json          the catalog an app reads, assembled from index/ without the `build` blocks
preview/index.html  a page to listen on
```

## Writing a recipe

Copy `recipes/forest.py` to `recipes/<biome>.py` (the biome id from `../species/biomes.json`) and change the
sounds. A recipe is plain Python that starts with `from lib import *` and defines three functions:

```python
def day(s):    return left, right     # two lists of exactly s.n floats: the day bed
def night(s):  return left, right     # the night bed
def cues(s):   return [cue(...), ...] # the cues, each naming the beds it plays over
```

`s` is a `Studio`: `s.n` (samples in a bed, 1 440 000), `s.seconds` (30), `s.rate` (48 000), `s.biome`, `s.part`
(`"day"`, `"night"` or `"cues"`), and `s.rng(name)`, a `random.Random` seeded from (biome, part, name). Give every
layer and every cue its own name, so changing one leaves the others' random draws alone.

A cue is `cue(id, samples, beds=["day"], every=[180, 600], level=-6, spread=0.6)` (the defaults are a far, rare cue):

- `id`: lower-case words and hyphens; the file is `cues/<biome>-<id>.ogg`.
- `samples`: a mono list at any level. The build trims silence off both ends, fades 3 ms in and out, scales the
  cue so its loudest 100 ms has an RMS of -20 dBFS, bends any peak above -13 dBFS softly towards -7 dBFS, and pads
  20 ms of silence at each end. With the padding a cue must be 0.2 to 4 s long.
- `beds`: `"day"`, `"night"` or both. Each bed needs four to six cues.
- `every`: seconds between two of this cue, `[min, max]`. An app sounds a cue first at `random * max` after the
  bed starts and then every `min + random * (max - min)`. The minimum may not be under 60 s.
- `level`: dB of gain the app plays the file at, over the bed played at 0. Every cue file's loudest 100 ms is 6 dB
  over a nominal bed RMS of -26 dBFS, so 0 is a near, clear call and -6 about level with the bed; beds are set by
  loudness now and sit from about 2.5 dB under that RMS to 0.5 over, so the build prints each cue's `over bed` figure against the
  real bed (its loudest 100 ms at its level, minus that bed's RMS); the forest's run from -4.9 (the far twig) to +5.9 (the day's hero).
- `spread`: how far from the centre the app may pan it, 0 (centre) to 1 (anywhere).

An optional `LEVEL = {"day": 0.0, "night": -2.0}` sets a bed's suggested level in dB (default 0).

**Cues are rare, and mostly far.** Real nature is not that active. A cue sounds every few minutes, not every few
seconds: a bed's commonest cue (usually its hero) has `every` about [90, 240], the others [180, 600] or rarer, so a
listener hears roughly one event a minute or less, with silences of several minutes possible. The build prints each
bed's expected events a minute (each cue once per mean of its `every`); the forest's are 0.85 by day and 0.79 by
night. Most cues are far off: `distant()` in the recipe and a level of -4 to -9. Each bed may have one hero, the
one sound that says where you are, which may be nearer (level 0 to -3) but still soft-edged (a bird's phrase, an
owl, not a knock). Nothing sharp or sudden near the listener: the check fails a bed with more than one cue above
level -4, and a cue above -4 whose loudest 5 ms is more than 6 dB over its loudest 100 ms (a knock, a snap, a
click). A sharp sound may be in a bed, far off and rare (the forest's twig at night: level -9, every 5 to 15
minutes).

**Beds are soft and dark.** A bed is a backdrop, played quietly under everything; the first version's days were
harsh. The build sets every bed to the same loudness and softens any bed brighter than the ceiling (below, "What
the build does to a bed"), so a bright recipe still comes out within the rules, but a recipe should not lean on
that: a bed made dark is better than a bright one shelved. The forest day keeps its crowns' rush under about
1.8 kHz and its leaves to a faint, dull rustle (puffs of noise from 1.5 to 5.5 kHz), and lands at 10% of its energy
above 2 kHz with no softening (the first version had 44%).

**The rule: a bed holds only continuous texture**, with slow, irregular movement. Every distinct event (a bird
phrase, a knock, a splash, a bell) is a cue. A 30 s loop with a recognisable event in it is heard as a loop. The
check's `stand` measure enforces it, and catches more than birds: in the forest it flagged leaves that fell silent
the moment a gust ended, a gust that rose 12 dB in the 2-8 kHz band, and the edges of a long lull. The second
forest's wind wanders about 4 dB, with a new level about every 6 s. If `stand` fires, make the movement shallower or
slower, give a layer that follows the wind a floor, or use more, smaller grains or voices; do not raise the limit.
Because seeds decide where things fall, the first forest recipe was also built under five other biomes' seeds:
every bed passed (the worst `stand` was 3.7 dB). Do the same with a new recipe before trusting it: one lucky seed
proves little.

### Loop mode

The build calls `day` and `night` in loop mode and `cues` in one-shot mode, and every toolkit function that cares
reads the mode, so a recipe never passes it. In loop mode a bed is made on a circle of exactly `s.n` samples:
noise is drawn for that circle, every filter runs around it (it first runs over the end of the buffer until its
impulse response has fallen 140 dB, so its state at sample 0 is its state after the last sample), control curves
are periodic over the bed, and every grain or call placed near the end wraps round to the start. So a bed is
periodic by construction, with no crossfade: a crossfade between two parts of a noise dips in level and blurs
whatever passes through it, and it cannot make a filter's state or a slow curve meet itself. `soft_limit` and
gains are memoryless, so they keep a loop a loop. The one way to break it is to do your own sample-by-sample work
with state (a hand-written filter, or `x[i + 1]` past the end); the `seam` check would then fail.

### What the build does to a bed

In order (`lib/finish.py`):

1. Takes out DC and everything under 50 Hz (afconvert's Opus encoder drops most of it anyway: measured -11 dB at
   10-30 Hz and -4.5 dB at 30-60 Hz, and a phone plays none of it).
2. Softens the top: when more than the ceiling's share of the energy is above 2 kHz or above 8 kHz (day 25% and
   4%, night 40% and 4%), it cuts with high shelves at 8 kHz and 2 kHz, round by round (at most 12 dB each), until
   the bed is 3 points under the 2 kHz ceiling and 1 point under the 8 kHz one. The build prints how much it cut
   ("softened -10.9 dB over 2k"); 0 means the recipe was dark enough by itself.
3. Sets the loudness to -24 LUFS (K-weighted, ungated, run around the loop) and bends anything near -3 dBFS under
   it with the soft limiter. Until 2026-11-14 beds were set to an RMS of -26 dBFS, and bright beds came out up to
   3.7 dB louder than dark ones; at one loudness they should sound alike in level, and their RMS lies from about 2.5 dB under -26 to 0.5 over.
4. Encodes (below), decodes, and if the codec moved the loudness more than 0.25 dB, encodes again with the
   difference; if the decoded file is over a brightness ceiling (the codec's noise can add a little on top of a
   quiet bed), softens once more from the decoded file's shares and encodes again.

## The toolkit

Everything below comes with `from lib import *`. Signals are lists of floats; a stereo signal is a pair
`(left, right)`. Frequencies are Hz, times seconds, levels dB. `rng` is a `random.Random` (from `s.rng(name)`).
`loop=None` means "the build's mode"; pass True or False only to override it.

Constants: `RATE` 48000, `BED_SECONDS` 30, `CONTROL_RATE` 100 (points a second in a control curve), `NOISE_RMS` 0.25.

Noise (`lib/noise.py`), each `n` samples at RMS 0.25:

```
white(n, rng)                        flat
pink(n, rng, loop=None)              -3 dB/octave: the base of wind and water
brown(n, rng, corner=60.0, loop=None) -6 dB/octave above `corner`: rumble, body, distant surf
blue(n, rng, loop=None)              +3 dB/octave: hiss, spray
rms(x); set_rms(x, target=0.25)
```

Filters (`lib/filters.py`), biquads from the RBJ cookbook:

```
lowpass(x, hz, q=0.7071, loop=None)       highpass(x, hz, q=0.7071, loop=None)
bandpass(x, hz, q=1.0, loop=None)         0 dB at hz; q 10 rings
band(x, lo, hi, loop=None)                keeps lo..hi
peak(x, hz, q=1.0, gain_db=6.0, loop=None)
highshelf(x, hz, gain_db, q=0.7071, loop=None)
onepole_lowpass(x, hz, loop=None)         onepole_highpass(x, hz, loop=None)
moving_lowpass(x, hz, loop=None)          one-pole whose cutoff follows a control curve in Hz
allpass(x, delay, g=0.5, loop=None)       Schroeder all-pass (slow: two passes in loop mode)
```

Control curves (`lib/control.py`): lists at `CONTROL_RATE`, periodic over the bed.

```
drift(rng, seconds, every=4.0, lo=0.0, hi=1.0, jitter=0.6)   smooth random wandering, a knot about every `every` s
gusts(rng, seconds, count, rise=(1.5, 4.0), fall=(2.5, 7.0), size=(0.35, 1.0), loop=None)  swells at random times
swell(seconds, cycles, lo=0.0, hi=1.0, phase=0.0)            a sine, whole cycles a bed (regular: use sparingly)
constant(seconds, value); points(seconds)
scale(curve, lo, hi)            a 0..1 curve onto lo..hi
smooth(curve, seconds, loop=None)
stretch(curve, n, loop=None)    to audio rate
apply(x, curve, loop=None)      x times the curve
```

Many small sounds (`lib/scatter.py`), each returning a stereo pair of `n` samples:

```
scatter(n, rng, count, grain, level=(-12, 0), pan=(-1, 1), follow=None, depth=1.0, loop=None)
    `count` grains, `grain(rng) -> list` called per grain, at random times, levels and positions; with `follow`
    (a control curve) more and louder where the curve is high. Rustle, drips, rain, crackle.
chorus(n, rng, voices, voice, rate=(1, 2), jitter=0.15, level=(-12, 0), pan=(-1, 1), presence=(0, 1), every=6.0, loop=None)
    `voices` callers; `voice(rng)` is called once per caller and returns its `call(rng) -> list`. Each calls on
    its own rate (calls a second), a whole number of times a loop, fading in and out on its own drift within
    `presence`. Crickets, frogs, cicadas.
```

Mixing (`lib/mix.py`):

```
mix(*layers)                    stereo layers as (pair, db) or pair: mix((wind, 0), (leaves, -6))
stereo(a, b, width=0.6)         two independent mono signals as middle and sides; correlation (1-w^2)/(1+w^2)
widen(pair, width=0.6)          mid/side width of a pair
pan(x, position); pan_gains(position)    equal power, -1 left to 1 right
decorrelate(x, rng, stages=3, loop=None) same spectrum, scrambled phase (slow; independent noise is cheaper)
gain(x, db); add(*signals); remove_dc(x)
soft_limit(x, ceiling_db=-3.5, knee_db=6.0)
place(buf, x, start, gain=1.0, loop=None)  add x into buf at a sample, wrapping in loop mode
```

Voices for cues (`lib/voices.py`), mono, starting and ending at silence:

```
tone(seconds, hz, harmonics=((1, 1.0),), attack=0.01, release=0.05, curve=1.0, vibrato=(0, 0), tremolo=(0, 0), breath=0.0, rng=None)
    hz: a number, (from, to), or [(share of the length, Hz), ...]
chirp(seconds, hz_from, hz_to)               phrase(rng, notes=6, hz=(2600, 5200), note=(0.05, 0.14), gap=(0.02, 0.07), shape=None)
trill(rng, count=10, hz=4200, each=0.025, gap=0.018, slide=0.0)
hoot(hz=380, seconds=0.45, fall=0.92, breath=0.08, rng=None)     caw(rng, hz=620, seconds=0.3)
croak(rng, hz=180, seconds=0.35, pulse=40)   churr(rng, seconds=3.0, hz=1100, pulse=(26, 30), shifts=2)
knock(rng, hz=900, seconds=0.12, q=7.0, body=0.5)                roll(rng, count=14, rate=16, hz=950, accel=0.0, fade=0.5, seconds_each=0.07)
snap(rng, seconds=0.35)                      creak(rng, seconds=1.2, rate=(25, 70), hz=(420, 1100), q=6.0)
bell(hz, seconds=2.5, partials=((ratio, level, decay seconds), ...), attack=0.003)
noise_burst(rng, seconds, lo=200, hi=6000, attack=0.005, release=0.05, curve=1.0)
envelope(seconds, attack=0.01, release=0.05, curve=1.0); decay(seconds, tau, attack=0.002)
seq(*parts); overlay(base, x, at, gain=1.0); silence(seconds); trim(x, floor_db=-60)
distant(x, amount=0.5)                       duller and softer; 1 is far
space(x, rng, seconds=0.9, wet=0.25, damp=4000)   a short open-air tail (Schroeder: four combs, two all-passes)
```

Also `cue(...)` (above), `db(x)`, `undb(d)` and `samples(seconds)`.

## index.json

```
{ "version": 1,
  "base": "https://qrx-pack.apphaus.us/soundscapes/",     every "file" below is relative to this
  "format": { "codec": "opus", "container": "ogg", "rate": 48000, "bedSeconds": 30, "bedChannels": 2,
              "cueChannels": 1, "bedRmsDb": -26.0, "cueLoudDb": -20.0, "bedLufs": -24.0, "level": "..." },
  "biomes": [ { "id": "forest", "code": 10, "name": "Forest",
                "beds": { "day": { "file": "beds/forest-day.ogg", "bytes": 148505, "level": 0.0 }, "night": {...} },
                "cues": [ { "id": "owl", "file": "cues/forest-owl.ogg", "bytes": 7996, "seconds": 2.946,
                            "beds": ["night"], "every": [90.0, 240.0], "level": -2.0, "spread": 0.8 }, ... ],
                "calls": [ "species/sounds/bat-call.wav", ... ] } ] }
```

The shape is as it was in the first version; `bedLufs` (2026-11-14) is the loudness every bed is now set to.
`bedRmsDb` stays, with a narrower meaning: it was the RMS every bed was normalised to, and is now the nominal bed
RMS that `cueLoudDb` and cue levels are written against (beds sit from about 2.5 dB under it to 0.5 over). `level` is still dB over the
bed. Biomes appear in `biomes.json`'s order, only those built. `calls` are the `call` sounds of the species whose `biome`
is this one in `../species/index.json`, as paths from the pack's root, for an app to scatter the local creatures'
own voices in the distance. They are WAV files, made by the species build, not here.

## Encoding

afconvert encodes Opus only into CAF; `lib/opus.py` moves the packets into an Ogg container with OpusHead and
OpusTags headers (RFC 7845), ported from TranceX's `tool/audio/make_content_sounds.py`. Beds are encoded at
afconvert's 40 kbps target, cues at 24 kbps.

**The seam, without hiss (2026-11-14).** A bed is encoded as two laps of its loop in a row, with 200 ms of its end
before the first and 200 ms of its start after the second; the file keeps only the packets of the second lap and
the 200 ms before it, and the Ogg header's pre-skip tells the decoder to run that 200 ms and drop it (RFC 7845's
pre-roll, which asks for at least 80 ms), and the last page's granule position ends it at exactly 30 s. So the
first decoded sample continues the encoder's own coding of the last one, and the codec's error runs on across the
wrap. The file is the same size as one lap's.

Why: the first version coded each bed once, with 200 ms of context either side. The two sides of the wrap were
then coded 30 s apart, each with its own error, and Opus's error at 40 kbps is as large as a dark bed's own signal
(peak error 0.04 to 0.07 beside an RMS of 0.05, measured), though it moves smoothly from sample to sample. At the
wrap two independent errors met, a real step of about the codec's error, large beside the few thousandths a dark
bed moves per sample. Six of the first eleven recipes added high hiss to pass `seam`. Measured on three dark beds
with their hiss taken out (tundra night and day, town night), decoded seam and slope against the limit of 1.0:

| bed | one lap, 40 kbps | 64 kbps | 96 kbps | 128 kbps | two laps, 40 kbps | 300 cuts inside the decoded file (worst) |
| --- | --- | --- | --- | --- | --- | --- |
| tundra night | 0.52/2.14 | 0.10/1.87 | 0.26/0.63 | 0.17/1.26 | 0.26/0.54 | 0.81 |
| town night | 1.02/2.61 | 1.04/2.10 | 0.02/0.27 | 0.18/0.21 | 0.16/0.25 | 0.77 |
| tundra day | 0.86/1.37 | 0.62/1.11 | 0.38/0.19 | 0.10/0.44 | 0.44/0.29 | 0.85 |

A higher bitrate helps, but not reliably (tundra night fails again at 128 kbps) and at up to 2.5 times the size;
two laps fixes all three at 40 kbps, and leaves the wrap no worse than any other point of the file (the last
column: the same measure at 300 random points inside each decoded file). With the whole build (softening,
loudness) the hiss-free tundra and town nights came out at 0.17/0.34 and 0.33/0.13. The build still has a
bitrate ladder behind it (40, 64, 96, 128 kbps): when a bed's decoded seam or slope is over 0.8 it encodes again
at the next step, and the fragment's `build.bitrate` and the bed's `bytes` say what was used. No bed has needed it
since the two laps.

A decoder that follows RFC 7845 returns exactly the 30 s; afconvert, WebKit and Chromium honour the pre-skip
(below). A player that ignores pre-skip would play 200 ms of the end before the start, and a loop 30.2 s long.

## Checks

Printed after every build and by `--check`, measured on the decoded files (`build.py` decodes each with afconvert).
The limits are in `lib/measure.py`.

Beds:

| measure | what | limit |
| --- | --- | --- |
| `peak` | highest sample, dBFS | under -3 |
| `rms` | both channels, dBFS | none (beds are set by loudness) |
| `lufs` | loudness after BS.1770's K-weighting, ungated | -24 +- 1 |
| `>2k`, `>8k` | share of the energy above 2 kHz and above 8 kHz | day at most 25% and 4%, night 40% and 4% |
| `dc` | the larger channel mean, dBFS | under -50 |
| `corr` | left/right correlation | 0.05 to 0.90 |
| `seam` | step across the wrap over 4x the RMS of the steps in the 50 ms around it; then the same for the second difference (a kink), larger channel | each at most 1.0 |
| `spread` | loudest 250 ms window over the median window, dB | at most 10 |
| `stand` | most one 250 ms window rises over the median of the windows 0.5 to 2 s either side; and one 1 s window over 2 to 6 s either side; over the whole and each band with 5% of the energy | at most 4 dB |
| `bands` | share of energy below 250 Hz, 250 Hz-2 kHz, 2-8 kHz, above 8 kHz | none: a fingerprint |

The build also prints `source seam`, the seam of the samples before encoding (it fails if that is over 1.0), the
bitrate each step of the ladder tried, and how much the softening cut.

Why those numbers. -24 LUFS is the quiet end of the first eleven (they ran from -24.1 to -20.4); one loudness for
every bed lets an app use one level. The brightness ceilings: the owner found the days harsh, and the first days
had 21 to 74% of their energy above 2 kHz and up to 40% above 8 kHz; the town day (21.5%) and tundra day (10%) were
the softest. 25% keeps a day at about the town day's brightness or darker; the redone forest day sits at 10% and
still has its crowns' rush. 4% above 8 kHz allows air but no hiss. Nights got a looser 40% because crickets live
at 4 to 5 kHz and the owner did not complain of the nights; three cricket nights (meadow 78%, mangrove 66%,
scrub 64%) are over it and will be softened or reworked.

Cues: `peak` under -3 dBFS; length 0.2 to 4 s; `edges`, the loudest sample in the first and last 5 ms, at least
40 dB under the peak; not silent; `snap`, the loudest 5 ms over the loudest 100 ms (printed; used below).
Per bed: no cue's `every` minimum under 60 s; at most one cue with a level above -4 (the hero); no cue above -4 with
a snap over 6 dB; four to six cues; and the expected events a minute is printed (aim at about one or fewer). After encoding, every file must decode to its exact frame count and must not be
silence. When the codec pushes a cue's peak to within 1 dB of the limit (sharp clicks overshoot by up to 3.5 dB),
the build takes that cue down by as much and encodes it again.

`--check` also fails when a recipe changed since its biome was built (by hash), when a built biome's recipe is
gone, when `calls` no longer match `../species/index.json`, when a cue file is not in its fragment, when a recipe
has no biome, and (with no biome named) when `index.json` is not what the fragments make.

How sensitive `stand` is (measured on the first forest): each forest cue was mixed once into its bed at its own
level and measured. Every one was
caught (8.5 to 14.9 dB on the day bed for the woodpecker, the two songbirds and the crow, 5.6 for the twig; 4.3 to
14.9 on the night bed). The churr, three seconds long, slipped through the 250 ms scale (2.6 dB) and is why the 1 s
scale exists (9.4 dB with it).

The forest's last build, and the first version's for comparison:

```
second version (2026-11-14)
day    peak -11.5  rms -26.6  lufs -24.2  >2k  9.9%  >8k 1.2%  dc -98  corr 0.32  seam 0.08/0.43  spread 2.4  stand 1.5 (<250)    bands 55.6 34.5  8.7  1.2
night  peak -11.0  rms -26.1  lufs -24.0  >2k 12.3%  >8k 1.2%  dc -76  corr 0.48  seam 0.08/0.06  spread 2.1  stand 2.8 (2k-8k)  bands 73.1 14.6 11.1  1.2
       both at 40 kbps, softened by 0 dB; cues 0.85 events a minute by day, 0.79 by night

first version (2026-11-13)
day    peak  -8.0  rms -26.0  lufs -21.9  >2k 44.1%  >8k 13.6%  dc -80  corr 0.48  seam 0.12/0.23  spread 3.2  stand 2.4 (>8k)   bands 30.1 25.8 30.5 13.6
night  peak -10.2  rms -26.0  lufs -22.9  >2k 28.7%  >8k  2.7%  dc -71  corr 0.53  seam 0.07/0.11  spread 2.0  stand 2.3 (2k-8k) bands 59.0 12.4 26.0  2.7
       cues 6.68 events a minute by day (the warble every 12 to 35 s), 3.88 by night
```

## Listening

What is on `master` plays at https://qrx-pack.apphaus.us/soundscapes/preview/ about a minute after a push. To hear
a build that is not pushed yet, serve the checkout:

```
cd third_party/QRX.pack && python3 -m http.server 8000
# then http://127.0.0.1:8000/soundscapes/preview/
```

The page reads `../index.json` and `../../species/biomes.json`, lists all eleven biomes (those not built are shown
as not built yet), loops the chosen bed from a decoded AudioBuffer (an `<audio loop>` element leaves a gap),
scatters that bed's cues as the apps do (each first at `random * every.max` after the bed starts, then every
`every.min + random * (every.max - every.min)`, with a random pan within its `spread`), shows which cue comes next
and when, with a line saying cues are rare on purpose, and has a button to fire each cue now, a volume slider and,
off by default, the biome's creature calls, dulled, far off and as rare as a cue (one every two to five minutes).

Which browsers decode the files: on this Mac (macOS 27.0.1), the system's WebKit, which Safari 27.0.1 uses, decoded
both forest beds and two cues with `decodeAudioData` to their exact frame counts (tried from a small WKWebView
program, not in Safari itself), and said `probably` to `audio/ogg; codecs=opus`. Chromium 156 (the Claude app's
browser pane) decoded the same four files to the same frame counts, played the day bed on the preview page and
logged no errors. The two-lap files of the second forest (2026-11-14) decode to exactly 1 440 000 frames in both;
their decoded seam measures 0.05/0.43 and 0.08/0.06 (day, night; the larger channel) in Chromium, as in
afconvert, and 0.35/0.68 and 0.37/0.74 in WebKit, whose decoder starts the pre-roll a little differently (its first
sample differs from afconvert's; its last is the same): still under the limit of 1.0. Not tried: Safari on iOS or
iPadOS, Firefox, older Safari. Where a browser cannot decode them, the
page says so, and `--wav` writes WAVs any player opens.

## Found while writing the eleven

Things the ten later recipes ran into, for whoever writes or changes one:

- A dark bed could fail `seam` after encoding though its source loop was clean, and farm night, town day and
  night, tundra day and night and mangrove day carry a trace of high hiss or fine high texture for that reason
  (commented in the recipes). **That is fixed in the build, not in recipes: take the hiss out.** The step was real
  (two independent codec errors meeting at the wrap); beds are now encoded in two laps ("Encoding" above), and
  tundra and town nights with their hiss removed pass at 40 kbps.
- A steady sine that loops exactly can make the source `seam` read just over 1 (a stack of beating partials has a
  high crest). Narrow bands of noise do not.
- `knock()` puts its thump at about a fifth of its pitch, so a low knock's thump lands at 30 to 60 Hz, which the
  codec drops, and the cue comes out quieter than its target with no fault. Use `body=0` and noise bursts for low
  knocks (town's door and ball).
- Clicky cues (a crab's claw, a frost tick, a dragonfly) measure several dB under the cue target because the
  limiter bends their peaks; their `level` was raised to make up for it.
- Second pass (2026-11-14): as first written, every one of the other ten had cues with an `every` minimum under
  60 s (5 to 7 events a minute), most had two to four near cues, several near cues were sharp, and 13 of their 20
  beds were louder than -24 LUFS or over a brightness ceiling (or both). Their authors redid them dark by design:
  no bed needs the build's softening, the hiss added for the seam is out of all six beds that carried it, and the
  cues dropped are the scrub's seedpod, the meadow's pipit, the barrens' skitter, the mangrove's crab and
  mudskipper, the tundra's mosquito and the marsh's near frog.
- What going this soft cost: the beds are much closer to each other than the first version's. Town day and forest
  day have nearly the same four-band shares; barrens day is close to both; mangrove and tundra, and the marsh's
  day and night, now differ more in what is in them and how slowly it moves than in any band. The mangrove night's
  chorus is about 2% of its energy and the barrens night's ticks 0.5%: either may not be heard. If two biomes
  sound alike, those faint layers are what to raise (a night has room up to 40% above 2 kHz).
- `s.rng(name)` returns a new generator with the same seed on every call, so call it once and keep it when
  drawing in a loop.
- The toolkit has no amplitude-pulse modulator; `recipes/shrub.py` has its own (`pulsed`, a whole number of
  pulses over the loop).
- Scrub night and meadow night both keep a far cricket layer (22% and 24% above 2 kHz); they differ by pitch and
  rhythm, which the bands do not show.

## Not verified

- The owner listened once, on the preview page, to the first version of all eleven, and found the day beds harsh
  and the cues far too frequent. Nobody has heard the second version (the redone forest, the softening, the
  loudness, the two-lap seam, the sparse cues). Whether a step at the wrap could be heard at all was never
  listened for; the two laps remove it by measure. Only the first forest's cues were mixed into their beds to see
  that `stand` catches them.
- Whether the softening's shelves sound natural on a bright recipe (they cut up to 12 dB at 2 kHz and at 8 kHz),
  or merely dull it: a recipe made dark is the intended way, and the cut is printed so it can be seen.
- In an app: QRay's phone and headset apps read `index.json` and play these through SoundLib's soundscape since
  2026-11-14, and a test on each platform plays the forest's day bed and a cue through SoundLib offline. It
  decodes the second version's files with no failure, and the bed repeats every 30.0000 s (measured on the
  iPhone's build: the pre-skip is honoured and the second lap's packets loop). Nobody has heard a bed from a
  device, the cues there have no pan (`spread` is unused) and `calls` is unused.
- Whether the levels suit a phone speaker: every bed has the same loudness by BS.1770's weighting, which is a
  model of ears, not ears; the cue levels were set from the `over bed` figure, not by ear.
- Whether decoders other than afconvert, WebKit and Chromium honour a pre-skip that covers a 200 ms pre-roll
  started at an arbitrary packet (the files now begin with the packets of a second lap). The size of the pre-skip
  is the same as before.
- The measures are proxies. `stand` catches the cues it was tried with, but a quiet event, or a slow pattern
  longer than six seconds, could pass it.
- Opus bytes on another macOS version, and the build on any machine but the owner's Mac.
