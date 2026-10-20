# QRX.pack

Public glyph content for [QRX](https://github.com/apphaus2/QRX): the documents a QR code points at, and the
bodies, minds, sounds and images they use. QRX bundles `glyphs/` (to share over Bluetooth and for its Demo
button), and anything here can be fetched by URL, so a printed code works for anyone.

Encode a *payload* below into a QR code (any generator works) and point QRX at it. Each payload is the
document's URL on qrx.apphaus.us, with an optional `size:` line first ([GLYPH.md](https://github.com/apphaus2/QRX/blob/master/docs/GLYPH.md)
in QRX describes the format).

| glyph | what it shows | payload |
| --- | --- | --- |
| [image.json](glyphs/image.json) | the test card | `https://qrx.apphaus.us/glyphs/image.json` |
| [video.json](glyphs/video.json) | a looping sample video | `size: *2`<br>`https://qrx.apphaus.us/glyphs/video.json` |
| [web.json](glyphs/web.json) | a web page | `size: 10l10x20b10`<br>`https://qrx.apphaus.us/glyphs/web.json` |
| [button.json](glyphs/button.json) | a button that shows a toast | `https://qrx.apphaus.us/glyphs/button.json` |
| [ui-login.json](glyphs/ui-login.json) | a JsonUI form, fields from `shared/fields.json` | `size: *3`<br>`https://qrx.apphaus.us/glyphs/ui-login.json` |
| [ui-survey.json](glyphs/ui-survey.json) | a JsonUI survey | `https://qrx.apphaus.us/glyphs/ui-survey.json` |
| [scene-bush.json](glyphs/scene-bush.json) | a singing bush that stands on the code and sings when tapped | `size: *4`<br>`https://qrx.apphaus.us/glyphs/scene-bush.json` |
| [scene-fox-butterfly.json](glyphs/scene-fox-butterfly.json) | Rusty the fox and Flit the butterfly on the floor: Rusty wanders and comes when tapped, Flit flutters about and rests on his back now and then | `size: *4`<br>`https://qrx.apphaus.us/glyphs/scene-fox-butterfly.json` |
| [scene-pet.json](glyphs/scene-pet.json) | Rusty as a house pet: he wanders the floor, gets hungry, sleepy and bored as the minutes pass, eats from his bowl, sleeps on his bed (or by the couch, where a headset knows one), and comes when tapped or spoken to | `size: *4`<br>`https://qrx.apphaus.us/glyphs/scene-pet.json` |
| [scene-aquarium.json](glyphs/scene-aquarium.json) | an aquarium: five reef fish in a glass tank with sand and plants; tap a fish and it darts away, tap the tank and they come up to feed. On a TV the tank fills the screen | `size: *4`<br>`https://qrx.apphaus.us/glyphs/scene-aquarium.json` |
| [scene-tank.json](glyphs/scene-tank.json) | the aquarium's tank with nobody in it: tap it to feed whatever a TV drops in. A TV looks it up once and puts every creature its phones captured in it | `size: *4`<br>`https://qrx.apphaus.us/glyphs/scene-tank.json` |
| [creature-fish.json](glyphs/creature-fish.json), [creature-fish-blue.json](glyphs/creature-fish-blue.json) | one reef fish on its own, swimming in the tank's volume by the code: a creature to find out in the world and keep. Its header says `"habitat": "water"`, so a QRX phone that scans it keeps it in its storage and a paired TV drops it into the tank (`scene-tank.json`) it keeps rather than onto its shelf | `size: *4`<br>`https://qrx.apphaus.us/glyphs/creature-fish.json` |
| [scene-trout.json](glyphs/scene-trout.json) | Speckle the trout, half a metre long, swimming slowly through the room at head height; tap and she swims over | `size: *4`<br>`https://qrx.apphaus.us/glyphs/scene-trout.json` |

The scenes are [JsonScene](https://github.com/apphaus2/JsonScene) documents; their minds are
[JsonMind](https://github.com/apphaus2/JsonMind) fragments.

A *creature* is a scene whose `_ui` header has a `habitat` (`"water"` now; `"ground"` for a terrarium later) and whose
actors are all mobile: QRX keeps it when a phone scans it and a TV merges its actors into the habitat's own scene
(`scene-tank.json` for water). Its `bounds` are replaced by the habitat scene's, and its `_ui.state` keys are its own
(each copy of a creature on a TV gets its own); `drift` and `places` are not carried over.

## Layout

```
glyphs/          the documents a code points at; QRX bundles this folder
glyphs/shared/   JsonUI fragments the forms reference
glyphs/bodies/   actor bodies: a model URL, scale, animation clips, sockets
glyphs/minds/    actor minds: persona, senses, canned replies, token budget
images/, sounds/ media the documents use by URL
models/          our own glTF models (CC0), written by the scripts
scripts/         assets.py makes the test card and the sounds; bush.py, butterfly.py, pet.py, fish.py and tank.py the models
                 (the bush, the butterfly, the pet's bowl and bed, the reef fish and the trout, the aquarium's tank):
                 `python3 scripts/bush.py .`, `python3 scripts/pet.py .`, `python3 scripts/fish.py .`
```

References inside `glyphs/` are relative (`bodies/fox.json`), so the folder works from any host. Media URLs
are absolute: `https://qrx.apphaus.us/images/...`, `.../sounds/...` and `.../models/...`.

## Hosting

https://qrx.apphaus.us, QRX's website ([QRX.site](https://github.com/apphaus2/QRX.site)), serves this repository's
`glyphs/`, `images/`, `sounds/` and `models/` at the same paths (`/glyphs/image.json`), from the commit it pins as
`third_party/QRX.pack`. So a push here goes live once QRX.site bumps the pin and deploys; check with
`curl -sI https://qrx.apphaus.us/glyphs/image.json`.

The domain is what printed codes carry, so it outlives a rename of this repository. Codes printed with the
older `raw.githubusercontent.com/apphaus2/QRX.pack/master/...` URLs keep working while the repository stays
public and the files stay where they are.

## Rules

- Everything here is public and released with QRX. Keep out anything that can't be: other people's
  characters, music or artwork, and anything internal. Internal development content lives elsewhere.
- New original content is CC0 (see [LICENSE](LICENSE)); generated assets keep their script here, so nothing is
  sampled. Third-party assets are referenced by URL, not copied (unless CC0, then under `models/` with their source),
  and are credited in [ATTRIBUTION.md](ATTRIBUTION.md).
- Changing a document changes what printed codes show. Rename only with a new file; keep the old one
  working. `scene-fox-duck.json` (Rusty and Pip the duck, replaced by `scene-fox-butterfly.json`) and
  `bodies/duck.json` stay for the codes printed with them.
