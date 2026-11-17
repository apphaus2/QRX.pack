# Blue Skylark (`blue-skylark`)

Lark: A sky-blue lark that sings while hanging high over open grass.

| | |
| --- | --- |
| found in | meadow (home: Meadow) |
| rarity | rare |
| habitat | air (flies) |
| size | **0.16 m** long |
| clips | `idle`, `fly`, `jump`, `spin`, `flip` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a bird's body: a side view; never changed once an image is made from it):

> A young lark with sky-blue plumage, darker blue wings and crown, a cream belly, a small crest, a short grey beak and a forked tail, on a short-mown path through a summer meadow, the tall grass and flowers well behind it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The bird stands still on the ground, side-on, facing left, in a relaxed standing pose: head level and looking ahead, wings folded at its sides, both feet on the ground and in view, its tail in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (bird): 0.16 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
