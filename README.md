# QRX.pack

Public glyph content for [QRX](https://github.com/apphaus2/QRX): the documents a QR code points at, and the
bodies, minds, sounds and images they use. QRX bundles `glyphs/` (to share over Bluetooth and for its Demo
button), and anything here can be fetched by URL, so a printed code works for anyone.

Encode a *payload* below into a QR code (any generator works) and point QRX at it. Each payload is the
document's raw URL, with an optional `size:` line first ([GLYPH.md](https://github.com/apphaus2/QRX/blob/master/docs/GLYPH.md)
in QRX describes the format).

| glyph | what it shows | payload |
| --- | --- | --- |
| [image.json](glyphs/image.json) | the test card | `https://raw.githubusercontent.com/apphaus2/QRX.pack/master/glyphs/image.json` |
| [video.json](glyphs/video.json) | a looping sample video | `size: *2`<br>`https://raw.githubusercontent.com/apphaus2/QRX.pack/master/glyphs/video.json` |
| [web.json](glyphs/web.json) | a web page | `size: 10l10x20b10`<br>`https://raw.githubusercontent.com/apphaus2/QRX.pack/master/glyphs/web.json` |
| [button.json](glyphs/button.json) | a button that shows a toast | `https://raw.githubusercontent.com/apphaus2/QRX.pack/master/glyphs/button.json` |
| [ui-login.json](glyphs/ui-login.json) | a JsonUI form, fields from `shared/fields.json` | `size: *3`<br>`https://raw.githubusercontent.com/apphaus2/QRX.pack/master/glyphs/ui-login.json` |
| [ui-survey.json](glyphs/ui-survey.json) | a JsonUI survey | `https://raw.githubusercontent.com/apphaus2/QRX.pack/master/glyphs/ui-survey.json` |
| [scene-bush.json](glyphs/scene-bush.json) | a singing bush that stands on the code and sings when tapped | `size: *4`<br>`https://raw.githubusercontent.com/apphaus2/QRX.pack/master/glyphs/scene-bush.json` |
| [scene-fox-duck.json](glyphs/scene-fox-duck.json) | Rusty the fox and Pip the duck on the floor: Rusty wanders and comes when tapped, Pip rides on his back | `size: *4`<br>`https://raw.githubusercontent.com/apphaus2/QRX.pack/master/glyphs/scene-fox-duck.json` |

The scenes are [JsonScene](https://github.com/apphaus2/JsonScene) documents; their minds are
[JsonMind](https://github.com/apphaus2/JsonMind) fragments.

## Layout

```
glyphs/          the documents a code points at; QRX bundles this folder
glyphs/shared/   JsonUI fragments the forms reference
glyphs/bodies/   actor bodies: a model URL, scale, animation clips, sockets
glyphs/minds/    actor minds: persona, senses, canned replies, token budget
images/, sounds/ media the documents use by URL
```

References inside `glyphs/` are relative (`bodies/fox.json`), so the folder works from any host. Media URLs
are absolute raw URLs of this repository.

## Rules

- Everything here is public and released with QRX. Keep out anything that can't be: other people's
  characters, music or artwork, and anything internal. Internal development content lives elsewhere.
- New original content is CC0 (see [LICENSE](LICENSE)). Third-party assets are referenced by URL, not
  copied, and are credited in [ATTRIBUTION.md](ATTRIBUTION.md).
- Changing a document changes what printed codes show. Rename only with a new file; keep the old one
  working.
