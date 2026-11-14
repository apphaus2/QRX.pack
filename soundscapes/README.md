# Soundscapes

Quiet background sound for each of the 11 biomes in `../species/biomes.json`, for an app to play while a
creature of that biome is out. Per biome there are two beds, `day` and `night` (30 s, stereo, 48 kHz, seamless
loops), and four to six cues per bed (short mono one-shots the app scatters over the bed at random). The format
is Ogg Opus, which SoundLib's soundscape plays.

Everything is synthesized here from noise and tones with fixed seeds. Nothing is recorded or downloaded, so it is
CC0 like the rest of the pack's generated sound. It is stylised on purpose.

Listen to them at **https://qrx-pack.apphaus.us/soundscapes/preview/** (the page in `preview/`, served from this
repository's `master`): pick a biome, Day or Night, and it loops the bed and scatters the cues as an app would.

All eleven biomes are built. The numbers under "Checks" stand in for ears while a recipe is written: they say a bed
is at the right level, loops without a step, is not mono and has no single moment that stands out; they do not say
it sounds good. Only listening does.

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

The forest builds in about 30 s on the owner's Mac (day bed 8 s, night bed 6 s, its eight cues 3 s; the rest is
encoding, decoding and measuring). `--check` of one biome takes about 7 s. Its files total 358 KB: the beds are
148 KB and 174 KB, the cues 1 to 10 KB each. `wav/` is ignored by git.

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

A cue is `cue(id, samples, beds=["day"], every=[min, max], level=-3, spread=0.6)`:

- `id`: lower-case words and hyphens; the file is `cues/<biome>-<id>.ogg`.
- `samples`: a mono list at any level. The build trims silence off both ends, fades 3 ms in and out, scales the
  cue so its loudest 100 ms has an RMS of -20 dBFS, bends any peak above -13 dBFS softly towards -7 dBFS, and pads
  20 ms of silence at each end. With the padding a cue must be 0.2 to 4 s long.
- `beds`: `"day"`, `"night"` or both. Each bed needs four to six cues.
- `every`: seconds between two of this cue, `[min, max]`.
- `level`: dB of gain the app plays the file at, over the bed played at 0. Every cue file's loudest 100 ms is 6 dB
  over a bed's RMS, so 0 is a near, clear call, -6 is level with the bed, lower is far off. The build prints each
  cue's `over bed` figure (its loudest 100 ms at its level, minus the bed's RMS); the forest's run from -0.3 to
  +7.2 dB.
- `spread`: how far from the centre the app may pan it, 0 (centre) to 1 (anywhere).

An optional `LEVEL = {"day": 0.0, "night": -2.0}` sets a bed's suggested level in dB (default 0).

**The rule: a bed holds only continuous texture**, with slow, irregular movement. Every distinct event (a bird
phrase, a knock, a splash, a bell) is a cue. A 30 s loop with a recognisable event in it is heard as a loop. The
check's `stand` measure enforces it, and catches more than birds: in the forest it flagged leaves that fell silent
the moment a gust ended, a gust that rose 12 dB in the 2-8 kHz band, and the edges of a long lull. What passed was
wind that wanders about 5 dB, with a new level about every 5 s. If `stand` fires, make the movement shallower or
slower, give a layer that follows the wind a floor, or use more, smaller grains or voices; do not raise the limit.
Because seeds decide where things fall, the forest recipe was also built under five other biomes' seeds: every bed
passed (the worst `stand` was 3.7 dB). Do the same with a new recipe before trusting it: one lucky seed proves little.

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

It takes out DC and everything under 50 Hz (afconvert's Opus encoder drops most of it anyway: measured -11 dB at
10-30 Hz and -4.5 dB at 30-60 Hz, and a phone plays none of it), sets the RMS of both channels to -26 dBFS, and
bends anything near -3 dBFS under it with the soft limiter. After encoding it decodes the file, and if the codec
left the RMS more than 0.25 dB off, encodes again with that much more gain.

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
              "cueChannels": 1, "bedRmsDb": -26.0, "cueLoudDb": -20.0, "level": "..." },
  "biomes": [ { "id": "forest", "code": 10, "name": "Forest",
                "beds": { "day": { "file": "beds/forest-day.ogg", "bytes": 148505, "level": 0.0 }, "night": {...} },
                "cues": [ { "id": "owl", "file": "cues/forest-owl.ogg", "bytes": 7996, "seconds": 2.946,
                            "beds": ["night"], "every": [25.0, 70.0], "level": -1.0, "spread": 0.8 }, ... ],
                "calls": [ "species/sounds/bat-call.wav", ... ] } ] }
```

Biomes appear in `biomes.json`'s order, only those built. `calls` are the `call` sounds of the species whose `biome`
is this one in `../species/index.json`, as paths from the pack's root, for an app to scatter the local creatures'
own voices in the distance. They are WAV files, made by the species build, not here.

## Encoding

afconvert encodes Opus only into CAF; `lib/opus.py` moves the packets into an Ogg container with OpusHead and
OpusTags headers (RFC 7845), ported from TranceX's `tool/audio/make_content_sounds.py`. Beds are encoded at
afconvert's 40 kbps target, cues at 24 kbps.

A bed is encoded with 200 ms of its own end before it and of its own start after it, and the Ogg header's pre-skip
and the last page's granule position tell the decoder to drop that extra. So the codec codes the seam as the middle
of a sound. Without it the decoded seam was measurably worse (on one night bed the kink across the seam was 1.23 to 1.33
times the limit with 20 ms of context and 0.23 with 200 ms). A decoder that follows RFC 7845 returns exactly the
30 s; afconvert, WebKit and Chromium do (below). A player that ignores pre-skip would play 200 ms of the end before
the start, and a loop 30.2 s long.

## Checks

Printed after every build and by `--check`, measured on the decoded files (`build.py` decodes each with afconvert).
The limits are in `lib/measure.py`.

Beds:

| measure | what | limit |
| --- | --- | --- |
| `peak` | highest sample, dBFS | under -3 |
| `rms` | both channels, dBFS | -26 +- 1 |
| `lufs` | loudness after BS.1770's K-weighting, ungated | none: compare biomes by it |
| `dc` | the larger channel mean, dBFS | under -50 |
| `corr` | left/right correlation | 0.05 to 0.90 |
| `seam` | step across the wrap over 4x the RMS of the steps in the 50 ms around it; then the same for the second difference (a kink), larger channel | each at most 1.0 |
| `spread` | loudest 250 ms window over the median window, dB | at most 10 |
| `stand` | most one 250 ms window rises over the median of the windows 0.5 to 2 s either side; and one 1 s window over 2 to 6 s either side; over the whole and each band with 5% of the energy | at most 4 dB |
| `bands` | share of energy below 250 Hz, 250 Hz-2 kHz, 2-8 kHz, above 8 kHz | none: a fingerprint |

The build also prints `source seam`, the seam of the samples before encoding, and fails if it is over 1.0.

Cues: `peak` under -3 dBFS; length 0.2 to 4 s; `edges`, the loudest sample in the first and last 5 ms, at least
40 dB under the peak; not silent. After encoding, every file must decode to its exact frame count and must not be
silence. When the codec pushes a cue's peak to within 1 dB of the limit (sharp clicks overshoot by up to 3.5 dB),
the build takes that cue down by as much and encodes it again.

`--check` also fails when a recipe changed since its biome was built (by hash), when a built biome's recipe is
gone, when `calls` no longer match `../species/index.json`, when a cue file is not in its fragment, when a recipe
has no biome, and (with no biome named) when `index.json` is not what the fragments make.

How sensitive `stand` is: each forest cue was mixed once into its bed at its own level and measured. Every one was
caught (8.5 to 14.9 dB on the day bed for the woodpecker, the two songbirds and the crow, 5.6 for the twig; 4.3 to
14.9 on the night bed). The churr, three seconds long, slipped through the 250 ms scale (2.6 dB) and is why the 1 s
scale exists (9.4 dB with it).

The forest's last build:

```
day    peak -8.0  rms -26.0  lufs -21.9  dc -80  corr 0.48  seam 0.12/0.23  spread 3.2  stand 2.4 (>8k)     bands 30.1 25.8 30.5 13.6
night  peak -10.2 rms -26.0  lufs -22.9  dc -71  corr 0.53  seam 0.07/0.11  spread 2.0  stand 2.3 (2k-8k)   bands 59.0 12.4 26.0  2.7
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
scatters that bed's cues at their `every` intervals with a random pan within their `spread` (the first of each
within 15 s), and has a button to fire each cue, a volume slider and, off by default, the biome's creature calls,
dulled and far off.

Which browsers decode the files: on this Mac (macOS 27.0.1), the system's WebKit, which Safari 27.0.1 uses, decoded
both forest beds and two cues with `decodeAudioData` to their exact frame counts (tried from a small WKWebView
program, not in Safari itself), and said `probably` to `audio/ogg; codecs=opus`. Chromium 156 (the Claude app's
browser pane) decoded the same four files to the same frame counts, played the day bed on the preview page and
logged no errors. Not tried: Safari on iOS or iPadOS, Firefox, older Safari. Where a browser cannot decode them, the
page says so, and `--wav` writes WAVs any player opens.

## Found while writing the eleven

Things the ten later recipes ran into, for whoever writes or changes one:

- A dark bed can fail `seam` after encoding though its source loop is clean. The two sides of the wrap are coded
  30 s apart, and Opus's error at 40 kbps, small beside the signal, is large beside how little a signal with
  nothing above 4 to 8 kHz moves from one sample to the next. Farm night, town day and night, tundra day and night
  and mangrove day each carry a trace of high hiss or fine high texture for this reason (commented in the
  recipes), which changes the sound to pass a measure. Whether the step it guards against can be heard as a tick
  is not known; if it cannot, the measure should change and the hiss go. Town night (0.61/0.82), wetland day
  (0.78/0.91), mangrove night (0.21/0.81) and tundra day (0.51/0.69) are the nearest to the limit of 1.0.
- A steady sine that loops exactly can make the source `seam` read just over 1 (a stack of beating partials has a
  high crest). Narrow bands of noise do not.
- `knock()` puts its thump at about a fifth of its pitch, so a low knock's thump lands at 30 to 60 Hz, which the
  codec drops, and the cue comes out quieter than its target with no fault. Use `body=0` and noise bursts for low
  knocks (town's door and ball).
- Clicky cues (a crab's claw, a frost tick, a dragonfly) measure several dB under the cue target because the
  limiter bends their peaks; their `level` was raised to make up for it.
- `s.rng(name)` returns a new generator with the same seed on every call, so call it once and keep it when
  drawing in a loop.
- The toolkit has no amplitude-pulse modulator; `recipes/shrub.py` has its own (`pulsed`, a whole number of
  pulses over the loop).
- Scrub night and meadow night are the closest pair in the four bands (both mostly crickets at 2 to 8 kHz); they
  differ by pitch and rhythm, which the bands do not show. Tundra's day and night differ least of any biome's.

## Not verified

- Nobody has listened to a bed or a cue, in the browser, on a phone or anywhere. Whether a biome sounds like its
  place, whether it is pleasant, whether two biomes can be told apart and whether a loop is heard as a loop are
  unknown. Only the forest's cues were mixed into their beds to see that `stand` catches them.
- Whether SoundLib's soundscape decodes these files, honours the 200 ms pre-skip, loops a bed without a gap and
  places the cues as `every`, `level` and `spread` intend. Nothing in an app reads `index.json` yet.
- Whether the levels suit a phone speaker: every bed has the same RMS, but beds of different spectra differ in
  loudness (`lufs`), and the cue levels were set from the `over bed` figure, not by ear.
- The measures are proxies. `stand` catches the cues it was tried with, but a quiet event, or a slow pattern
  longer than six seconds, could pass it.
- Opus bytes on another macOS version, and the build on any machine but the owner's Mac.
