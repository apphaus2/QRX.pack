# Honeycrown Bee (`honeycrown-bee`)

Mead: A great dark bee with a ruff of gold, said to visit a meadow once a summer.

| | |
| --- | --- |
| found in | meadow (home: Meadow) |
| rarity | legendary |
| habitat | air (flies) |
| size | **0.09 m** long |
| clips | `idle`, `fly`, `dance`, `spin`, `flip`, `crown` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a bee's body: a side view; never changed once an image is made from it):

> A large bumblebee, deep chocolate brown and fluffy with bright golden-yellow bands, a thick golden ruff of fur round its neck, smoky wings and dark legs, on a short-mown path through a summer meadow, the tall grass and flowers well behind it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left: head level, all six legs on the ground and in view, its wings folded on its back. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (bee): 0.09 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
