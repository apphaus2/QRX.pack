# Species

The creatures QRay's players find in the world: small definitions, written by hand, that one command turns into
finished creatures (a JsonScene document and a glTF model each) and a catalog an app can pick a spawn from.

This folder is content and the tool that makes it. Nothing in the apps reads it yet. Paths below are from the
root of QRX.pack, where this folder lives (`species/`).

```
python3 species/build.py            # build everything, then check it
python3 species/build.py --check    # check the definitions and what is on disk, write nothing; exit 1 on a fault
```

Python 3.9 or later, standard library only. The build is deterministic: the same definitions write the same bytes.

## Two axes

A species sits on two axes that have nothing to do with each other.

- **Biome: where it is found.** One of the 11 land-cover classes of ESA WorldCover (the 10 m global land-cover
  map; the class codes and names are from its product user manual, v100 2020 and v200 2021; only the codes and
  names are used here, no data). An app looks up the land cover where the player stands, gets a code, and
  `index.json` says what spawns there. `biomes.json` is the list.
- **Habitat: how it moves and where it is kept.** `water`, `ground` or `air`: the three TV habitats (the Tank, the
  Terrarium, the Aviary). It is the `habitat` the apps already read from a creature's `_ui` header
  (`GlyphDocument.habitat`), so it stays exactly those three values. `habitats.json` is the list.

A marsh has a swimmer, a walker and a flier; a desert has no fish. The biome decides who turns up, the habitat
decides which tank it goes in afterwards.

| code | WorldCover class | biome id | shown as |
| --- | --- | --- | --- |
| 10 | Tree cover | `forest` | Forest |
| 20 | Shrubland | `shrub` | Scrub |
| 30 | Grassland | `meadow` | Meadow |
| 40 | Cropland | `farm` | Farmland |
| 50 | Built-up | `town` | Town |
| 60 | Bare / sparse vegetation | `barren` | Barrens |
| 70 | Snow and ice | `snow` | Snowfield |
| 80 | Permanent water bodies | `water` | Open Water |
| 90 | Herbaceous wetland | `wetland` | Marsh |
| 95 | Mangroves | `mangrove` | Mangrove |
| 100 | Moss and lichen | `tundra` | Tundra |

The biome `water` and the habitat `water` share a word and nothing else: a goldfish is at home in the biome `town`
and lives in the habitat `water`.

## Layout

```
build.py                 the one command
biomes.json              the biomes: WorldCover code, id, name, colour, description, least roster, and `home`, the
                         phrase a creature met there says it lives in
habitats.json            the habitats: bounds (QRX.pack's README), how creatures move in them, how big they may be
rarity.json              the rarity levels: spawn weight, colour, what the creature itself gets
reserved.json            ids and names QRX.pack already uses
life.json                what a spawned creature's own name, age and temperament are drawn from
mind.json                what every creature's mind shares: token defaults, speech registers, closing lines, budget,
                         canned rules, which sound a tap or an approach gets
tricks.json              every trick: its phrases, and what a behaviour trick does
sounds.json              the voices: a synthesized sound for each of four meanings
definitions/<biome>/     the source of truth: one <id>.json per species, in its home biome's folder
lib/shapes.py            parts: ellipsoids, tubes, lofts, fins, wing sheets; vectors and quaternions
lib/gltf.py              the .glb writer, and the reader --check measures models with
lib/builder.py           what an archetype builds with: colours, patterns, clips, rarity's features, the motes
lib/behaviour.py         tempers: what a creature does when tapped
lib/mind.py              the mind written into each document, and what --check holds it to
lib/tricks.py            which tricks a species knows, their handlers and the rules that hear them
lib/sounds.py            the sound synthesizers and the WAV writer and reader
lib/archetypes/*.py      one module per kind of animal
creatures/<id>.json      built: the creature's scene document
models/<id>.glb          built: its model
sounds/<voice>-<meaning>.wav   built: the sounds
index.json               built: the catalog
ROSTER.md                built: every species by biome, with its chance there
preview/index.html       every model in a browser
```

`creatures/`, `models/`, `sounds/`, `index.json` and `ROSTER.md` are written by `build.py` and checked in. Do not edit them:
`--check` compares them byte for byte with what the definitions build.

## A definition

```json
{
  "id": "ember-skink",
  "name": "Cinder",
  "species": "Ember Skink",
  "description": "A dark skink banded like cooling lava, with a sail that glows at night.",
  "prompt": "I am {name}, an ember skink, dark with bands like cooling lava and a sail on my back that glows at night. I am {age} and I live in {home}, among black rocks that stay warm long after sunset. I am solitary and wary, and I slip into a crack when I am tapped, glowing a little brighter as I go. Others of my kind say I am {temperament}, and they are right. My voice is low and smouldering, with a hiss in it, and I talk of warmth, embers and the dark rocks.",
  "temperament": "shy",
  "biomes": ["barren"],
  "habitat": "ground",
  "rarity": "epic",
  "archetype": "lizard",
  "size": 0.24,
  "shape": {"crest": "sail"},
  "colours": {"body": "#3A2A28", "belly": "#5A3A30", "pattern": "#FF6A2B", "trim": "#FFB84A", "toe": "#5A3A30", "accent": "#FF7A2E", "glow": "#FF8A3D"},
  "pattern": {"type": "bands", "count": 5, "width": 0.3, "lit": true},
  "behaviour": {"temper": "shy", "distance": 2.2}
}
```

| key | meaning |
| --- | --- |
| `id` | the species: lower-case words joined by hyphens, the file's name, and the name of its outputs |
| `name` | this creature's own name ("Cinder"); what a player sees once it is caught. No two species share one |
| `species` | the species' name ("Ember Skink") |
| `description` | one line, at most 160 characters |
| `prompt` | the species speaking for itself, so a creature can be talked to: one line, 240 to 560 characters, in the first person, with the tokens `{name}`, `{age}`, `{home}` and `{temperament}`. See "Talking to a creature" |
| `speech` | optional: its speech register (`little`, `simple`, `clear`, `thoughtful`); its rarity's otherwise |
| `temperament` | optional: the species' typical nature, one of `life.json`'s `temperaments`; its archetype's otherwise (`temperaments` in `mind.json`). Only what `{temperament}` reads as for a copy of the template: a living creature has its own |
| `voice` | optional: a voice from `sounds.json` (`owl`, `fox`, `gecko`...); its archetype's otherwise. See "Sounds" |
| `tricks` | optional: exactly the tricks it knows, by id; otherwise the basics and the first of its archetype's. See "Tricks" |
| `signature` | a legendary's own trick: `{"id", "phrases", "move", "motes"}`. Required for a rarity with `signature`, refused for any other |
| `mind` | optional and rarely needed: an object whose keys (`senses`, `tools`, `budget`, `triggers`, `canned`) replace the shared ones from `mind.json` for this species |
| `biomes` | where it is found, the home biome first. The file lives in `definitions/<home>/`. A common species may list three, an uncommon one two; rare and above have one, so they are a reason to go somewhere (`maxBiomes` in `rarity.json`) |
| `habitat` | `water`, `ground` or `air` |
| `rarity` | a level from `rarity.json` |
| `archetype` | a module in `lib/archetypes` |
| `size` | metres. The archetype is drawn at its own `LENGTH` and scaled by `size / LENGTH`; fins, tails and ornaments can add to it, and `index.json` gives the size that came out |
| `shape` | optional: any of the archetype's `SHAPE` parameters |
| `colours` | optional: any of the archetype's `COLOURS` slots, as `#rrggbb` |
| `pattern` | optional: `{"type": ...}` from the archetype's `PATTERNS`, with that pattern's numbers; `"lit": true` paints it in the `glow` colour on a creature rare enough to glow |
| `movement` | optional: `speed` (m/s), `turnRate` (degrees/s), `pause` (`[shortest, longest]` seconds between wanders); the habitat's defaults otherwise |
| `behaviour` | optional: `temper` `shy` (tapped, it flees to `distance`), `curious` (it comes to within `distance`) or `calm` (it stops); `seconds` it lasts; `watch` to face the viewer |

Each archetype's docstring, `SHAPE`, `COLOURS`, `PATTERNS` and `CHOICES` at the top of its module say what it
takes. The body patterns most share (`lib/builder.py`, `painter`): `plain`, `bands`, `stripes`, `spots`, `saddle`,
`tips`. Winged ones have their own (`edged`, `eyespots`, `bands`, `veins`).

## Rarity

`rarity.json`. A species' chance in a biome is its weight over the sum of the weights of everything that spawns
there; away from its home biome a species counts for `visitorShare` (half) of its weight.

| level | weight | colour | biomes | what the creature gets | speaks | tricks |
| --- | --- | --- | --- | --- | --- | --- |
| common | 60 | `#8E9AA6` | up to 3 | its colours and one pattern | `little` | the basics and 2 |
| uncommon | 25 | `#3FA66B` | up to 2 | `trim`: the pattern is edged in a second colour | `little` | the basics and 2 |
| rare | 10 | `#3B82F6` | 1 | `ornament`: an extra part, by archetype (a crest, a horn, tail streamers, a coronet, spikes, long tentacles...) | `simple` | the basics and 3 |
| epic | 4 | `#A855F7` | 1 | `glow`: the ornament, and anything painted `"lit"`, is emissive at 0.6 | `clear` | the basics and 4 |
| legendary | 1 | `#F5B301` | 1 | glow at full strength and `motes`: a ring of five lights that circles it in every clip; lower, longer sounds | `thoughtful` | the basics, 4 and a signature |

So rarity shows on the creature, not only in its header: each level keeps what the one below has. In a biome with
the least roster (2 common, 1 uncommon, 1 rare, 1 epic, 1 legendary, no visitors) a legendary is 1 spawn in 160.

Adding a level is a row in `rarity.json`; `features` may hold `trim`, `ornament`, `glow` and `motes`. `speech` is
the level's default register, `tricks` how many of its archetype's tricks a species knows beside the basics, `sound`
a `pitch` and `length` for its voice, `signature` whether its species each have a trick of their own.

## What is built

**`creatures/<id>.json`** is a creature in the shape of QRX.pack's `creature-*.json`: a `Scene` with one mobile
actor, the habitat's `anchor`, the bounds and altitude the pack's creatures of that habitat use, `idle` and the
habitat's moving clip (`swim`, `walk`, `fly`), a one-shot clip for each trick it animates, four sounds, the tap
behaviour, a handler for each trick and a `mind` ("Talking to a creature", "Sounds", "Tricks"). Two things differ
from the pack:

- The body is inlined, not a `$ref` to `bodies/*.json`, so a document stands alone wherever an app keeps it
  (a relative `$ref` needs the document's URL as its base, and a bundled document has none).
- The header has seven more keys beside `habitat`:

  ```json
  "_ui": { "version": 1, "habitat": "ground", "species": "bark-skink", "rarity": "common", "biome": "forest", "biomes": ["forest", "shrub"],
           "tokens": { "name": "Twig", "age": "young", "home": "the woods nearby", "temperament": "lazy" },
           "homes": { "forest": "the woods nearby", "shrub": "the thickets nearby" },
           "tricks": [ { "id": "come", "phrases": ["come here", "come", "..."], "do": [ { "emit": "come" } ] }, "..." ],
           "state": { "scared": false } }
  ```

  `species`, `rarity`, `biome` (home) and `biomes` say what it is; `tokens` and `homes` are for filling in its prompt
  ("Talking to a creature"); `tricks` is what it can be asked to do ("Tricks").

  Extra header keys are harmless to today's apps: JsonUI's header parser (`JsonUIHeader(value:)`,
  `JsonUIHeader.fromValue`) reads only `version`, `state`, `script` and `strings`, and `GlyphDocument.habitat` reads
  `habitat` from the raw document on both platforms, which is how `habitat` itself already gets through. Two caveats:
  an app has to read the new keys the same way (from `GlyphDocument.value["_ui"]`, not from `JsonDocument.header`),
  and a document rebuilt from `JsonDocument.value` loses them, as it loses `habitat`. JsonUI's JSON schema says
  `_ui` takes no other keys, but nothing validates against it at run time and `habitat` is already outside it.

**`models/<id>.glb`**: 34 to 88 KB (the limit is 96; it was 80 before tricks), metres, +Y up, the head along +Z,
clips `idle` and the habitat's moving clip, both looping, and a one-shot clip for each trick the species animates. A walker's origin is on the ground under it, a swimmer's or flier's at mid-body. Plain coloured
materials (no textures), emissive for the glow.

**`index.json`**, for an app choosing a spawn:

```
codes      {"10": "forest", ...}                          land-cover code to biome id
biomes     [{id, code, name, worldcover, colour, home, description, weight, spawns: [{species, rarity, weight, home}]}]
           (a biome's `home` is its phrase, "the woods nearby"; a spawn row's `home` says whether the species is at home there)
life       {names, age, temperaments}
species    [{id, name, species, description, biome, biomes, habitat, rarity, weight, archetype,
             document, model, modelRef, size, bytes, triangles, speech, sounds: {call, content, alarm, curious}}]
rarities   [{id, name, weight, colour}]      habitats   [{id, name}]      modelBase, soundBase, visitorShare
```

"What can spawn in biome X, and how likely" is `biomes[X].spawns`: pick a row with probability
`row.weight / biome.weight`, then load `species[row.species].document`. The catalog has no prompts and, on purpose,
no tricks: an app has the document by the time anything can be said, and tricks are for the player to find.

### How the documents name their models

`--model-base` sets it (and `--sound-base` the sounds, which otherwise sit beside the models: `sounds/` for
`models/`); the choice is recorded in `index.json` and `--check` holds the documents to it. Every address the build
writes starts from one constant, `PACK` at the top of `build.py`: change it there, rebuild, and every document and
the catalog follow.

| base | `body.model` becomes | works where, today |
| --- | --- | --- |
| `bundle:` | `bundle:ember-skink.glb` | Only where an app ships the file and gives JsonScene a resolver for `bundle:` names. Today that is the TVs' habitat stages, for the habitats' own scenery; everywhere else `bundle:` resolves to nothing |
| an `https://` prefix (default) | `https://apphaus2.github.io/QRX.pack/species/models/ember-skink.glb` | Everywhere, as the pack's own creatures do (`https://qrx.apphaus.us/models/...`), once the files are served there; nothing serves these yet. Needs the network at spawn time; JsonScene caches the download |
| a relative prefix (`../models/`) | `../models/ember-skink.glb` | Nowhere today: a relative reference resolves against `AssetLocator.base`, and no app passes one |

The default is this repository's GitHub Pages address, `https://apphaus2.github.io/QRX.pack/species/models/` (the owner's call,
2026-11-12): species are not bundled in the apps and are not on the website. Pages serves this repository's `master`
exactly as it is (`.nojekyll` at the root: nothing is built), so a creature is named by its document's URL, exactly
what a printed code would carry, and every platform loads it the way it loads any glyph by URL:

```
https://apphaus2.github.io/QRX.pack/species/index.json            the catalog
https://apphaus2.github.io/QRX.pack/species/creatures/<id>.json   a creature
https://apphaus2.github.io/QRX.pack/species/models/<id>.glb       its model
https://apphaus2.github.io/QRX.pack/species/sounds/<name>.wav     a sound
```

A push to `master` publishes a change within a minute or so; Pages lets a client keep a file for ten minutes
(`max-age=600`). JSON is served as `application/json` and models as `model/gltf-binary`, with
`access-control-allow-origin: *`. A caught creature carries its address with it, so do not move or rename a species'
files once people can catch it; the address also changes if this repository is renamed, unless Pages is given a
domain of its own first. A spawn needs the network
the first time a species is seen; JsonScene keeps the model after that.

The model files are flat (`<id>.glb`) because the bundle resolvers take a bare file name. `reserved.json` keeps a
species from taking a name the pack's models use.

## Templates and life

A species here is a template: its document is public, and anyone can load it by its URL. An individual creature
exists only when the app spawns one out in the world, and only a spawned creature gets *life information* (`life`):
its own name, its age, where it was met and its temperament. `life.json` is what those are drawn from, and the build
copies it into `index.json` as `life`:

```
names          the pool a spawned creature's own name is picked from (the name in a species' definition, "Twig", is
               only the template's example)
age            { minDays, maxDays }: how old a creature can be when it is met
temperaments   the natures a creature can have, each one adjective that reads after "I am":
               shy, bold, playful, lazy, curious, gentle, grumpy, proud
```

The app picks them from the encounter, so two phones that meet the same creature agree on who it is. Where it was met
is a biome id, never a place. A creature loaded from a code or a URL, with no spawn, has no life information.

## Talking to a creature

The apps let a person talk to a scene: push-to-talk reaches each actor as a `spoken` event, and an actor with a
`mind` (JsonMind, part of JsonScene) answers through TokenLib when the player has set a key there. Every species has
a `prompt` for that, and the build writes it into the creature's document as its actor's mind. Two rules hold for
every creature:

- **With AI behind it, it speaks**, in the register of its kind: a mouse like a small child, an old owl in full
  sentences.
- **Without AI, or when nobody is attending to it, it goes back to sounds.** It never says a word unless a model
  wrote it, and nothing but the player speaking to it or tapping it can reach the model.

### Tokens

A prompt is written once for the species and filled in for the individual. A token is `{` + lower-case letters +
`}`; there are four, and a prompt uses no other braces:

| token | filled with | reads after | a living creature | a copy of the template |
| --- | --- | --- | --- | --- |
| `{name}` | the creature's own name | "I am" | `Hazel` (from `life.json`'s pool) | the species' example name, `Twig` |
| `{age}` | a ready phrase for its age | "I am" | `7 months old` | `young` (`tokens.age` in `mind.json`) |
| `{home}` | the `home` phrase of the biome it was met in | "I live in" | `the thickets nearby` (met in `shrub`) | the home biome's phrase, `the woods nearby` |
| `{temperament}` | its nature, one of `life.json`'s | "I am" | `bold` | the species' typical one: its definition's `temperament`, or its archetype's (`temperaments` in `mind.json`) |

The document's header carries what an app needs to fill them with nothing else to hand: `tokens` is what each token
reads as for a creature with no life information, and `homes` maps every biome the species is found in to its
phrase, so a creature whose life information says it was met in `shrub` reads "the thickets nearby". The phrases
are `home` in `biomes.json` (and in each biome of `index.json`).

```
template   I am {name}, a bark skink. I am {age} and I live in {home}, on an old log ... Others of my kind say I am {temperament}, and they are right.
living     I am Hazel, a bark skink. I am 7 months old and I live in the thickets nearby, on an old log ... Others of my kind say I am bold, and they are right.
a copy     I am Twig, a bark skink. I am young and I live in the woods nearby, on an old log ... Others of my kind say I am lazy, and they are right.
```

The apps' cores do the filling in just before a scene is built; the documents here always hold the tokens. A new
piece of life information is a new token: give it a default and use it.

### Registers: how a species speaks

`speech` in a definition, or its rarity's default (`speech` in `rarity.json`). Each register is one plain
instruction in `mind.json` (`registers`), which the build puts after the prompt, so the model is told how to speak in
words it can follow, not only that the creature is "child-like":

| register | default for | the creature is told |
| --- | --- | --- |
| `little` | common, uncommon | "I talk like a very small child: three to six little words at a time, about what I see, what I want and how I feel. My own animal worries keep pulling my thoughts away." |
| `simple` | rare | "I talk the way a child of six or seven does: one or two short, simple sentences of everyday words, full of wonder and of questions of my own." |
| `clear` | epic | "I speak in clear, complete sentences, one or two at a time, calmly and plainly, like someone who has seen a good deal and is in no hurry." |
| `thoughtful` | legendary | "I speak in full, thoughtful sentences, never more than two at a time, choosing each word with care, like one who has had a long while to think." |

Rarity is only the default: a rare owl is `clear`, a rare jerboa `little`, a legendary fox or hare `clear`. The
prompt gives the voice its character (what it sounds like, what it talks about); the register gives it its length.

### The mind the build writes

```json
"mind": {
  "persona": "<the prompt> <its register> <how a nature shows> <what it is> <its tricks are secret>",
  "senses": ["userDistance", "timeOfDay"],
  "tools": ["say", "sound", "lookAt", "play", "emit"],
  "budget": { "tokens": 8000, "perTurn": 1000, "cooldown": 8 },
  "triggers": ["spoken", "tap"],
  "canned": [
    { "match": "^spoken\\b.*\\b(can you jump|do a jump|jump up|jump|leap|hop)\\b", "do": [{ "emit": "jump" }] },
    "... one rule for each trick the species knows ...",
    { "match": "^spoken\\b.*\\b(what|who|where|why|how|...)\\b", "do": [{ "lookAt": "user" }, { "sound": "curious" }] },
    { "match": "^spoken\\b.*\\b(good|nice|pretty|clever|...)\\b", "do": [{ "lookAt": "user" }, { "sound": "content" }] },
    { "match": "^spoken", "do": [{ "lookAt": "user" }, { "sound": "call" }] },
    { "match": "^tap", "do": [{ "lookAt": "user" }] }
  ]
}
```

Everything but the prompt comes from `mind.json` and `tricks.json`, once for all species, and each choice follows
from how JsonMind behaves (JsonScene's `ActorSimulation` and `MindSession`; `lib/mind.py` has the same notes):

- **`persona`** is the species' prompt, then its register, then three things every creature shares: how a
  temperament shows (`nature`), that it is a wild animal, gentle with children, and does not understand anything
  unkind, unsafe or grown-up (`closing`), and that its tricks are a secret (`secret`). JsonMind puts the persona at
  the front of the system prompt.
- **What can make a creature spend tokens: the player speaking, or the player tapping it. Nothing else.** JsonMind
  has no way to say "this trigger is canned only": an event in `triggers` goes to the model whenever a provider is
  attached, the budget has room and the cooldown has passed. So `triggers` holds only the player's own acts. Someone
  coming near, time passing, another actor, an animation ending never wake the mind at all; those moments are the
  actor's own `on` handlers and behaviours, which always run and cost nothing.
- **The actor's own handlers are where the body lives.** An event runs the actor's `on` handler first and then, if
  it is a trigger, wakes the mind. `on.tap` makes the tap sound and sets `scared` (or `curious`, `still`) exactly
  as before; `on.near` makes a sound when the player comes close; `on.<trick>` does each trick. The mind adds
  to that and cannot undo it.
- **`tools`: `say`, `sound`, `lookAt`, `play`, `emit`.** Words, one of its sounds, a glance, one of its trick clips,
  and `emit`, which is how a canned rule does a trick (it fires the actor's own handler). `behave` and `moveTo` are
  left out because a mind's `behave` replaces the actor's whole behaviour list until another `behave`, which would
  switch the tap reaction off for good; `set` could leave a state key stuck. The canned rules pass through the same
  filter, so they use only these.
- **`canned`: no words, ever.** The rules answer when there is no provider, when the provider fails (no key) and
  when the budget is spent. They hear the tricks first, then answer a question with the `curious` sound, kind words
  with `content`, anything else with `call`, and a tap with a look (the tap's own sound came from `on.tap`).
  `--check` refuses a canned rule that says anything. The rules are tried in order and the first match wins:
  JsonMind chooses nothing at random, so a creature varies its answer by what was said, not by chance.
- **`senses`**: how far away the person is and the time of day. Not `state` or `actors`: on a TV those hold every
  creature in the habitat and would be paid for on every turn.
- **`budget`**: at most 1000 tokens a turn, 8000 for as long as the scene is up, and 8 seconds between turns, so
  tapping fast does not spend fast. `perTurn` cannot be smaller: JsonMind refuses a turn whose prompt it estimates
  above it (and falls back to the canned rules for good, since the prompt only grows), and a turn here is the system
  text (about 430 tokens) plus up to six remembered turns; `--check` adds that up for every species.

Three things this cannot guarantee from the document, because they are the host's or the library's:

- **Speech is not aimed.** The apps hand what was said to every actor of every scene in view, so three creatures on
  screen all hear it and, with a key, all answer and spend. Aiming speech at the creature the player is looking at
  is the app's job (`JsonSceneController.heard(_:by:)` takes an actor id; the apps pass none).
- **During the cooldown a mind does nothing.** JsonMind answers a turn that arrives inside the cooldown with an
  error, not with the canned rules, so for those 8 seconds speech gets no reaction (a tap still gets `on.tap`).
- **The budget is counted in memory.** It starts again each time the scene is built. TokenLib's own daily cap is
  the limit that lasts.

### What it costs the player

Nothing without a TokenLib key: the canned rules answer. With one, each spoken sentence or tap that gets through the
cooldown is one call: about 450 tokens in and 20 to 60 out on the first turn, rising to about 850 in once six turns
are remembered. A creature stops calling after 8000 tokens, roughly 10 to 15 exchanges, until its scene is built
again.

### Writing a prompt

- First person, one paragraph, a few sentences: what it is, where it lives, what it does all day, how it feels about
  people, what its voice is like. Start with "I am {name}, a ...".
- Use `{name}`, `{age}` and `{temperament}` after "I am" and `{home}` after "I live in" (or another "in"), so each
  reads as a sentence whatever fills it. Say where it lives with `{home}`, not in fixed words: a species found in
  two biomes must read right in both. Its own corner of the place ("under a stone", "in a pond") can follow in plain
  words. Give the temperament room: "I am {temperament}, for a skink" reads right for a shy one and a bold one.
- Say what a tap does, in keeping with its `temper` (it runs, it comes closer, it stays put): the body does that by
  itself and the words should agree with it.
- Give the voice a character, not a length: "My voice is gruff and snuffly but kind, and I talk mostly about smells
  and supper." The register says how much it says; do not repeat it, and do not contradict it.
  - `little`: write a small, busy, easily distracted animal with two or three things on its mind.
  - `simple`: the same, with room for wonder and a question back.
  - `clear`: an animal with some standing: calm, sure, a little dry or grand.
  - `thoughtful`: a legendary with a character of its own; say what it cares about and how it carries itself. An
    old owl is not a harvest hare.
- What a creature says is shown in a bubble and read aloud by the phone, so the voice must be speakable: no
  asterisks, no brackets, no stage directions.
- Do not name its tricks. It may be said to like showing off; what it can do is for the player to find.
- Keep it short. The prompt is sent with every turn; 240 to 560 characters is the allowed range.
- Original and safe for children: nothing from any game, show or brand, nothing frightening.

## Sounds

A creature with no model behind it answers in sounds, and one with a model may use them beside its words. Like a
cat that meows but also purrs, each has four, named by what they mean, the same names for every animal:

| sound | means | made when |
| --- | --- | --- |
| `call` | its ordinary call: a greeting, an answer | spoken to (no model), coming when called, starting most tricks |
| `content` | pleased and at ease: longer and softer | kind words (no model), a calm creature tapped or approached, staying, dancing |
| `alarm` | startled or scared | a shy creature tapped (with `scared`), hiding |
| `curious` | a question: what is that? | asked a question (no model), a shy creature approached, a curious one tapped |

`sounds.json` holds the voices. A voice gives each meaning a sound of its own, or borrows another meaning's (a
snail's `alarm` is its `call`; declared, never left out, so every document has all four names):

```json
"bird": { "call": { "kind": "chirp" }, "content": { "kind": "trill", "gain": 0.6 },
          "alarm": { "kind": "squeak", "pitch": 0.9, "length": 1.4 }, "curious": { "kind": "peep" } }
```

A `kind` is one of the small synthesizers in `lib/sounds.py` (chirp, peep, trill, squeak, hoot, coo, caw, yip,
thump, croak, buzz, purr, hum, bubble, click, puff, hiss, whoosh): a few tones and puffs of noise in a row, with a
`pitch` and a `length` (multipliers) and a `gain`. Nothing is sampled. Every archetype has a voice of its own name;
a definition's `voice` picks another (`owl`, `fox`, `hare`, `gecko`...). A rarity may vary them (`sound` in
`rarity.json`): a legendary's are a little lower and longer. The build writes each sound once to
`sounds/<voice>-<meaning>.wav` (with the variation in the name when there is one): 16-bit mono at 11025 Hz, 2 to 16
KB, quiet (a peak of 0.28 of full scale), starting and ending at silence. A file is at most 20 KB and a species'
four at most 48 KB together.

Which sound a moment gets is data: `on` in `mind.json` (tap and near, by temper), `canned` in `mind.json` (speech
with no model), and each trick's `sound` in `tricks.json`. The model sees the four names in its system prompt and
may play one with its words.

## Tricks

A creature does tricks when asked, like a dog that sits. It knows all of its species' tricks from the moment it is
caught, and **the player has to find them out**: nothing lists them. The catalog does not carry them, the persona
keeps them secret even when asked, and the apps show only the ones a player has already found (on that creature's
own page). `ROSTER.md` and the preview page list them, as spoilers for whoever works on the pack.

- **`tricks.json`** names every trick once: its id and four to seven phrases a person might say for it ("roll over",
  "roll", "do a roll", "can you roll over"), lower case, no punctuation. A phrase is heard on its own or inside a
  sentence. Within one species no trick's phrase may be inside another trick's, so asking for one never gets
  another.
- **An archetype** lists the tricks its body can do (`TRICKS`, the most guessable first) and animates each with
  `b.trick(id, seconds, rot=..., pos=..., scl=...)`: a one-shot clip named by the trick's id, built from whole-body
  moves (`full_turn`, `swing`, `lean`, `hold`, `lift`, `pulse`, `shrink`, `about` in `lib/builder.py`). A trick the
  archetype does not animate is a behaviour, written in `tricks.json` as commands (`do`): coming over, staying,
  speaking, hiding.
- **A species knows** the `basics` (`come`, `stay`, `speak`, `hide`: what people try first with any animal), then
  the first few of its archetype's (its rarity's `tricks`: 2 for a common, 4 for a legendary), or exactly the
  list its definition gives in `tricks`. Only the clips a species knows are put in its model.
- **A legendary has a `signature`**, one trick no other species has, meant to be guessable from its look or its
  name: `{"id": "snow", "phrases": ["make it snow", "snow", ...], "move": "headturn", "motes": "fall"}`. It borrows
  one of its archetype's moves and its motes leave their ring for it (`burst`, `swirl`, `gather`, `rise`, `fall`).

In a document every trick is an event named by its id:

```json
"_ui":   { "tricks": [ { "id": "jump", "phrases": ["jump", "hop", "jump up", ...], "do": [ { "emit": "jump" } ] } ] }
"body":  { "animations": { "jump": { "clip": "jump", "loop": false } } }
"on":    { "jump": [ { "behave": "idle" }, { "lookAt": "user" }, { "sound": "call" }, { "play": "jump" }, { "wait": 0.8 }, { "behave": "none" } ] }
```

The header is what an app matches speech against (or a remembered list against); running a trick is performing its
`do` on the actor, which fires the actor's own handler. The handler is inside the actor, so it survives a TV
renaming the creature's ids and state, and it costs no tokens. The mind's canned rules emit the same events, so
tricks work by voice with no TokenLib key. With a key, speech goes to the model first (JsonMind consults the canned
rules only when no model answers): the model is told the clip names and to do a trick when asked, but it cannot be
relied on, so an app should match the header's phrases itself before it lets the mind hear.

"Fetch" is not here: it needs something to fetch, and a creature's scene has only the creature.

**Adding a trick later** is all it takes to teach every creature of a species: add it to `tricks.json`, animate it
in the archetype (or give it a `do`), list it in the archetype's `TRICKS` or a definition's `tricks`, rebuild and
push. Creatures already caught know it the next time their document is fetched. A new clip changes the model file,
and a device that already downloaded that model keeps its copy until it fetches the model again; until then the
clip is missing there and the trick plays its sound and nothing else.

## Checking

`--check` rebuilds everything in memory and reads everything on disk, and fails on:

- **the tables**: a rarity without a weight or colour, a habitat with bad bounds, two biomes with one code;
- **a definition**: unknown or missing keys, an id that is not the file's name or that the pack uses, an unknown
  biome, habitat, rarity or archetype, a file in the wrong biome's folder, more biomes than its rarity allows, a
  shape parameter, colour slot or pattern the archetype does not have, an archetype whose origin does not suit the
  habitat, two species with one name;
- **a prompt**: missing, not one line, outside 240 to 560 characters, not starting with "I", without `{name}`, with
  a token that is not `name`, `age`, `home` or `temperament`, with a brace that is not part of a token, with an
  asterisk; a `speech` that is not a register, a `temperament` that is not one of `life.json`'s, a `voice` that is
  not in `sounds.json`;
- **tricks**: a trick that is not in `tricks.json` or that the archetype cannot do; a phrase that is not lower-case
  words, fewer than four phrases; within a species, a phrase of one trick inside a phrase of another; a legendary
  without a signature, a signature on anything else, a signature whose id or phrase another species has; a species
  with no tricks; a trick id that is one of JsonScene's events or clips;
- **the shared tables**: `mind.json` without a default for `age`, a register or closing line with braces, a canned
  rule that says words or uses a command outside the tools, a temper without its tap and near sounds, an archetype
  without a typical temperament; `sounds.json` with a voice that lacks a meaning or names an unknown kind, an
  archetype without a voice; a biome without a `home` phrase; a name in `life.json` that is a species' template
  name, a QRX.pack name or a token default, or that is not plain letters; temperaments that are not six to eight
  lower-case adjectives;
- **a model**, read back from disk by `lib/gltf.py`'s reader (not trusting the writer): the container and every
  accessor in bounds, unit normals, indices in range, triangles wound to face the way their normals do, unique
  node names (the iOS loader finds animation targets by name), the clips the habitat plays present and no others,
  every clip's keys rising from 0 with the last key equal to the first (so it loops), unit quaternions; its
  longest side within the habitat's `size`; the box it sweeps through every clip no more than half the habitat's
  bounds on any axis; a walker's lowest point on the ground, a swimmer's or flier's origin inside its body; its
  eyes not in the rear third (it faces +Z); at most 96 KB; a trick's clip may fling it about but not further than
  the habitat is wide, tall or deep;
- **a document**: the header keys, one mobile actor, the model reference under the recorded base, animations that
  name clips the model has and a model with no clip the body does not declare, sockets that name nodes it has,
  altitude inside the bounds, state it binds declared; `tokens` holding exactly the known tokens with the template's
  defaults, `homes` covering exactly the species' biomes with `tokens.home` the home biome's phrase; `tricks` equal
  to what the definition makes, each emitting its own event, each with an `on` handler of known commands, each clip
  it plays present and not looping; `on.tap` and `on.near` making a sound;
- **a sound**: every meaning naming a file that is on disk, a valid 16-bit mono WAV at the table's rate, at most
  20 KB and 0.9 s, quiet, starting and ending at silence; a species' sounds at most 48 KB together; no sound file
  that no species uses;
- **a mind**: equal to what the definition, `mind.json` and `tricks.json` make, its persona beginning with the
  definition's prompt, holding the secrecy rule and using only tokens the header can fill; tools other than `say`,
  `sound`, `lookAt`, `play` and `emit`; triggers other than `spoken` and `tap`; a budget over the caps or a
  cooldown under 5 seconds; a canned rule that says anything, uses a command that is not one of its tools (JsonMind
  would drop it), plays an unknown sound or emits an event the actor has no handler for; a trigger no canned rule
  answers; a trick whose first phrase, said in a sentence with no model, would not do it; a turn with a full history
  estimated above `perTurn`;
- **the catalog**: no tricks anywhere in it; every species listed once with the right biome, rarity, weight and files; each biome's spawn
  table equal to what the definitions say, weights included; the code table;
- **the rosters**: each biome has at least its `roster` of species at home, and one of every rarity;
- **staleness**: any built file that differs from what the definitions build now, and any built file no definition
  makes.

A plain `build.py` runs the same checks on what it has just written. Run it twice and compare the `sha256` it
prints to see the determinism for yourself; nothing in the output depends on the time, the machine or hash order.

## Adding things

**A species.** Write `definitions/<home biome>/<id>.json`, run `python3 species/build.py`. Look at it in the
preview. Faults are printed with the file they are in.

**An archetype.** Add `lib/archetypes/<name>.py`; it is found by its file name. It needs `HABITAT` (what it was
drawn for), `ORIGIN` (`"ground"` or `"centre"`), `LENGTH` (its longest side as drawn, metres), `SHAPE` and
`COLOURS` (parameters and slots with their defaults; `accent` and `glow` are expected), `PATTERNS`, optionally
`CHOICES` (the values a text parameter takes), and `build(b)`, which adds named nodes and two clips, `"idle"` and
`"move"`, to the `Builder` and returns `{"sockets": {"mouth": "<node>"}}`. The driver renames `move` to the
habitat's clip and adds a legendary's motes. Read `fish.py` (a lofted, painted body), `beetle.py` (legs and gaits)
and `bird.py` (wing sheets) first. Use `b.has("trim" | "ornament" | "glow")` to give rarity something to show,
`b.mat(slot, glow=True)` for parts that light up, `b.painted(part, painter(b, lo, hi))` for patterns and
`b.clip(name, seconds, keys, rot=..., pos=..., scl=...)` with functions of the clip's fraction 0 to 1.

**A trick.** Add it to `tricks.json` with four to seven phrases (and a `do` if it is a behaviour), animate it in each
archetype that can do it with `b.trick(...)` and add its id to that archetype's `TRICKS`. Species that take their
archetype's default set pick it up by its place in the list; others name it in `tricks`. See "Tricks" for what
devices that already have the model do.

**A voice.** Add it to `voices` in `sounds.json` with a sound for each of the four meanings (a `kind` from
`lib/sounds.py` with `pitch`, `length` and `gain`, or the name of another meaning to borrow), and name it in a
definition's `voice`. A new kind of sound is a few lines in `_kind` and its name in `KINDS`.

**A register.** Add a line to `registers` in `mind.json`: one instruction, in the first person, in plain words a model
can follow. Name it in a definition's `speech` or a rarity's.

**A habitat.** Add an entry to `habitats.json`: its TV `bounds`, the `wild` bounds a creature's own document
carries, `mode` (`ground` or `air`, JsonScene's two), `origin`, the moving clip's name, `anchor`, `start`, `size`
and the default `speed`, `turnRate` and `pause`. No code changes here; the apps and the TVs would need a habitat
scene for it (`KeptCreature.home`, QRX.pack's `habitats/`).

**A biome.** Add an entry to `biomes.json` with its land-cover `code`, an `id`, `name`, `colour`, `home` (a short
phrase that reads after "I live in": "the woods nearby"), `description`
and `roster` (the least number of species at home there), make `definitions/<id>/`, and write at least `roster`
species for it covering every rarity. No code changes.

## The preview

```
cd species && python3 -m http.server 8000      # then open http://localhost:8000/preview/
```

One page, grouped by biome, filtered by biome, habitat and rarity (a developer's page: it shows the tricks, which
are spoilers). Each card has a button for each trick, which plays its clip and its sound (a dashed button is a
behaviour, with nothing to play here), a button for each of its four sounds, and the model playing its moving
or idle clip, its name, species, rarity, habitat, archetype and its chance in that biome. "Visitors too" adds the
species that wander in from other biomes. three.js 0.160.0 from jsDelivr; the models load by relative path.

## The roster

[ROSTER.md](ROSTER.md) is the full table, rebuilt with everything else. The first batch (2026-11-12) is 77 species:
19 swimmers, 32 walkers and 26 fliers from 18 archetypes.

| biome | at home | who |
| --- | --- | --- |
| Forest 10 | 6 | Twig the Bark Skink, Acorn the Wood Mouse, Umber the Dusk Bat, Juniper the Emerald Swallowtail (rare), Bramble the Mossglow Stag Beetle (epic), Aurelia the Dawnplume (legendary) |
| Scrub 20 | 6 | Pepper the Banded Gecko, Peep the Hedge Finch, Nettle the Bramble Spider, Quill the Thornback Hedgehog (rare), Sable the Nightshade Moth (epic), Marigold the Sunfrill Lizard (legendary) |
| Meadow 30 | 6 | Dawdle the Meadow Snail, Petal the Meadow White, Bracken the Meadow Vole, Lark the Blue Skylark (rare), Prism the Glasswing (epic), Mead the Honeycrown Bee (legendary) |
| Farmland 40 | 6 | Barley the Field Bee, Button the Spotted Garden Beetle, Nibble the Harvest Mouse, Tawny the Granary Owl (rare), Sickle the Harvest Moon Moth (epic), Ceres the Golden Harvest Hare (legendary) |
| Town 50 | 12 | Drizzle the Garden Snail, Crumb the House Mouse, Flicker the Lamp Moth, Tango the Pond Goldfish, Cobble the Street Pigeon, Clink the Bottlecap Beetle, Jet the Cellar Spider, Soot the Chimney Bat, Brocade the Fountain Koi (rare), Copper the Rooftop Gecko (rare), Signal the Neon Darter (epic), Regent the Clocktower Raven (legendary) |
| Barrens 60 | 7 | Dune the Darkling Beetle, Grit the Sand Lizard, Mesa the Cliff Swift, Flint the Rock Scorpion, Skip the Longfoot Jerboa (rare), Cinder the Ember Skink (epic), Sol the Sun Scarab (legendary) |
| Snowfield 70 | 6 | Flurry the Snow Bunting, Drift the Snow Moth, Glint the Icefish, Mitten the Snowshoe Hare (rare), Shiver the Frost Jelly (epic), Boreal the Glacier Owl (legendary) |
| Open Water 80 | 9 | Bloop the Moon Jelly, Nib the Reed Seahorse, Pebble the Sand Minnow, Tumble the Pond Turtle, Skim the Speckled Ray, Thistle the Thorny Seahorse (rare), Plum the Violet Fantail (rare), Ribbon the Aurora Eel (epic), Nocturne the Starlit Ray (legendary) |
| Marsh 90 | 7 | Puddle the Pond Frog, Dart the Pond Skimmer, Noodle the Marsh Eel, Fern the Marsh Newt, Zephyr the Ruby Darter (rare), Marble the Glowspot Frog (epic), Lotus the Jade Turtle (legendary) |
| Mangrove 95 | 6 | Silt the Mangrove Goby, Skitter the Mud Crab, Murk the Mud Ray, Fiddle the One-Claw Crab (rare), Lumen the Lantern Jelly (epic), Halcyon the Mangrove Kingfisher (legendary) |
| Tundra 100 | 6 | Lichen the Moss Beetle, Bog the Tundra Lemming, Sedge the Arctic Skipper, Tarn the Arctic Char (rare), Verdigris the Boreal Emerald (epic), Nimbus the Northlight Fox (legendary) |

## Rules

- Names and designs are original: no names, likenesses or signature looks from any game, show or brand. Plain
  animals with friendly names.
- The four creatures in QRX.pack (`creature-fish`, `creature-fish-blue`, `creature-lizard`, `creature-butterfly`)
  stay where they are; `reserved.json` keeps their ids and names out of here.
- Everything here is generated from these scripts, so nothing is sampled from anyone else's work.
