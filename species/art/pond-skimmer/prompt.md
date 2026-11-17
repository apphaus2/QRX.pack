# Pond Skimmer (`pond-skimmer`)

Dart: A blue dragonfly that patrols the same stretch of bank all day.

| | |
| --- | --- |
| found in | wetland, water, meadow (home: Marsh) |
| rarity | common |
| habitat | air (flies) |
| size | **0.14 m** long |
| clips | `idle`, `fly`, `spin`, `flip` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a dragonfly's body: a top view, from directly above; never changed once an image is made from it):

> A skimmer dragonfly with a powder-blue body banded with fine black rings, dark eyes and clear wings, resting on a wide, flat expanse of plain pale grey rock that fills the whole frame, by a marsh. Natural wildlife photograph, realistic proportions. Camera directly above the animal and far away, looking straight down, a near-orthographic top view with a long lens: no wide angle, no tilt. The animal rests still with its head pointing to the left of the frame, all four wings spread flat and fully in view, its long body straight. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (dragonfly): 0.14 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
