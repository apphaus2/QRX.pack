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
biomes.json              the biomes: WorldCover code, id, name, colour, description, least roster
habitats.json            the habitats: bounds (QRX.pack's README), how creatures move in them, how big they may be
rarity.json              the rarity levels: spawn weight, colour, what the creature itself gets
reserved.json            ids and names QRX.pack already uses
definitions/<biome>/     the source of truth: one <id>.json per species, in its home biome's folder
lib/shapes.py            parts: ellipsoids, tubes, lofts, fins, wing sheets; vectors and quaternions
lib/gltf.py              the .glb writer, and the reader --check measures models with
lib/builder.py           what an archetype builds with: colours, patterns, clips, rarity's features, the motes
lib/behaviour.py         tempers: what a creature does when tapped
lib/archetypes/*.py      one module per kind of animal
creatures/<id>.json      built: the creature's scene document
models/<id>.glb          built: its model
index.json               built: the catalog
ROSTER.md                built: every species by biome, with its chance there
preview/index.html       every model in a browser
```

`creatures/`, `models/`, `index.json` and `ROSTER.md` are written by `build.py` and checked in. Do not edit them:
`--check` compares them byte for byte with what the definitions build.

## A definition

```json
{
  "id": "ember-skink",
  "name": "Cinder",
  "species": "Ember Skink",
  "description": "A dark skink banded like cooling lava, with a sail that glows at night.",
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

| level | weight | colour | biomes | what the creature gets |
| --- | --- | --- | --- | --- |
| common | 60 | `#8E9AA6` | up to 3 | its colours and one pattern |
| uncommon | 25 | `#3FA66B` | up to 2 | `trim`: the pattern is edged in a second colour |
| rare | 10 | `#3B82F6` | 1 | `ornament`: an extra part, by archetype (a crest, a horn, tail streamers, a coronet, spikes, long tentacles...) |
| epic | 4 | `#A855F7` | 1 | `glow`: the ornament, and anything painted `"lit"`, is emissive at 0.6 |
| legendary | 1 | `#F5B301` | 1 | glow at full strength and `motes`: a ring of five lights that circles it in every clip |

So rarity shows on the creature, not only in its header: each level keeps what the one below has. In a biome with
the least roster (2 common, 1 uncommon, 1 rare, 1 epic, 1 legendary, no visitors) a legendary is 1 spawn in 160.

Adding a level is a row in `rarity.json`; `features` may hold `trim`, `ornament`, `glow` and `motes`.

## What is built

**`creatures/<id>.json`** is a creature in the shape of QRX.pack's `creature-*.json`: a `Scene` with one mobile
actor, the habitat's `anchor`, the bounds and altitude the pack's creatures of that habitat use, `idle` and the
habitat's moving clip (`swim`, `walk`, `fly`), and the tap behaviour. Two things differ from the pack:

- The body is inlined, not a `$ref` to `bodies/*.json`, so a document stands alone wherever an app keeps it
  (a relative `$ref` needs the document's URL as its base, and a bundled document has none).
- The header has four more keys beside `habitat`:

  ```json
  "_ui": { "version": 1, "habitat": "ground", "species": "ember-skink", "rarity": "epic", "biome": "barren", "biomes": ["barren"], "state": { "scared": false } }
  ```

  Extra header keys are harmless to today's apps: JsonUI's header parser (`JsonUIHeader(value:)`,
  `JsonUIHeader.fromValue`) reads only `version`, `state`, `script` and `strings`, and `GlyphDocument.habitat` reads
  `habitat` from the raw document on both platforms, which is how `habitat` itself already gets through. Two caveats:
  an app has to read the new keys the same way (from `GlyphDocument.value["_ui"]`, not from `JsonDocument.header`),
  and a document rebuilt from `JsonDocument.value` loses them, as it loses `habitat`. JsonUI's JSON schema says
  `_ui` takes no other keys, but nothing validates against it at run time and `habitat` is already outside it.

**`models/<id>.glb`**: 30 to 80 KB, metres, +Y up, the head along +Z, clips `idle` and the habitat's moving clip,
both looping. A walker's origin is on the ground under it, a swimmer's or flier's at mid-body. Plain coloured
materials (no textures), emissive for the glow.

**`index.json`**, for an app choosing a spawn:

```
codes      {"10": "forest", ...}                          land-cover code to biome id
biomes     [{id, code, name, worldcover, colour, description, weight, spawns: [{species, rarity, weight, home}]}]
species    [{id, name, species, description, biome, biomes, habitat, rarity, weight, archetype,
             document, model, modelRef, size, bytes, triangles}]
rarities   [{id, name, weight, colour}]      habitats   [{id, name}]      modelBase, visitorShare
```

"What can spawn in biome X, and how likely" is `biomes[X].spawns`: pick a row with probability
`row.weight / biome.weight`, then load `species[row.species].document`.

### How the documents name their models

`--model-base` sets it; the choice is recorded in `index.json` and `--check` holds the documents to it.

| base | `body.model` becomes | works where, today |
| --- | --- | --- |
| `bundle:` | `bundle:ember-skink.glb` | Only where an app ships the file and gives JsonScene a resolver for `bundle:` names. Today that is the TVs' habitat stages, for the habitats' own scenery; everywhere else `bundle:` resolves to nothing |
| an `https://` prefix (default) | `https://qrx.apphaus.us/species/models/ember-skink.glb` | Everywhere, as the pack's own creatures do (`https://qrx.apphaus.us/models/...`), once the files are served there; nothing serves these yet. Needs the network at spawn time; JsonScene caches the download |
| a relative prefix (`../models/`) | `../models/ember-skink.glb` | Nowhere today: a relative reference resolves against `AssetLocator.base`, and no app passes one |

The default is `https://qrx.apphaus.us/species/models/` (the owner's call, 2026-11-12): species are not bundled in
the apps. They are served publicly and pulled by URL, so a creature is named by its document's URL, exactly what a
printed code would carry, and every platform loads it the way it loads the pack's creatures. The public layout is
`https://qrx.apphaus.us/species/index.json`, `.../species/creatures/<id>.json` and `.../species/models/<id>.glb`:
this folder's `index.json`, `creatures/` and `models/`, which QRX's site copies from its QRX.pack pin when it is built. Nothing is served
there until the site is deployed with them. A spawn needs the network the first time a species is seen; JsonScene
keeps the model after that.

The model files are flat (`<id>.glb`) because the bundle resolvers take a bare file name. `reserved.json` keeps a
species from taking a name the pack's models use.

## Checking

`--check` rebuilds everything in memory and reads everything on disk, and fails on:

- **the tables**: a rarity without a weight or colour, a habitat with bad bounds, two biomes with one code;
- **a definition**: unknown or missing keys, an id that is not the file's name or that the pack uses, an unknown
  biome, habitat, rarity or archetype, a file in the wrong biome's folder, more biomes than its rarity allows, a
  shape parameter, colour slot or pattern the archetype does not have, an archetype whose origin does not suit the
  habitat, two species with one name;
- **a model**, read back from disk by `lib/gltf.py`'s reader (not trusting the writer): the container and every
  accessor in bounds, unit normals, indices in range, triangles wound to face the way their normals do, unique
  node names (the iOS loader finds animation targets by name), the clips the habitat plays present and no others,
  every clip's keys rising from 0 with the last key equal to the first (so it loops), unit quaternions; its
  longest side within the habitat's `size`; the box it sweeps through every clip no more than half the habitat's
  bounds on any axis; a walker's lowest point on the ground, a swimmer's or flier's origin inside its body; its
  eyes not in the rear third (it faces +Z); at most 80 KB;
- **a document**: the header keys, one mobile actor, the model reference under the recorded base, animations that
  name clips the model has, sockets that name nodes it has, altitude inside the bounds, state it binds declared;
- **the catalog**: every species listed once with the right biome, rarity, weight and files; each biome's spawn
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

**A habitat.** Add an entry to `habitats.json`: its TV `bounds`, the `wild` bounds a creature's own document
carries, `mode` (`ground` or `air`, JsonScene's two), `origin`, the moving clip's name, `anchor`, `start`, `size`
and the default `speed`, `turnRate` and `pause`. No code changes here; the apps and the TVs would need a habitat
scene for it (`KeptCreature.home`, QRX.pack's `habitats/`).

**A biome.** Add an entry to `biomes.json` with its land-cover `code`, an `id`, `name`, `colour`, `description`
and `roster` (the least number of species at home there), make `definitions/<id>/`, and write at least `roster`
species for it covering every rarity. No code changes.

## The preview

```
cd species && python3 -m http.server 8000      # then open http://localhost:8000/preview/
```

One page, grouped by biome, filtered by biome, habitat and rarity; each card shows the model playing its moving
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
