# Dusk Bat (`dusk-bat`)

Umber: A brown bat that leaves its hollow tree as the light goes.

| | |
| --- | --- |
| found in | forest (home: Forest) |
| rarity | uncommon |
| habitat | air (flies) |
| size | **0.18 m** long |
| clips | `idle`, `fly`, `spin`, `flip` |
| status | render and cutout made; no mesh yet |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written in the manner of `../prompts.py`, with the shot fitted to a bat's body: a side view; never changed once an image is made from it):

> A young brown long-eared bat, warm brown fur with a paler belly, dark brown wing membranes and large oval ears, flying in the open air of a clearing in a temperate broadleaf forest, the trunks far behind it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The bat flies across the frame, side-on, facing left, both wings spread wide and raised, every wing and both feet in view, its head level and looking ahead. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Not made yet. When it is, to [SPEC.md](../SPEC.md) section 3 where it fits this body (bat): 0.18 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
