# Marsh Capybara (`marsh-capybara`)

Mellow: A barrel of a capybara, sandy brown and square-nosed, that nothing has ever managed to upset.

| | |
| --- | --- |
| found in | mangrove, wetland (home: Mangrove) |
| rarity | uncommon |
| habitat | ground (walks) |
| size | **0.27 m** nose to tail, at most 0.15 m tall in any clip |
| clips | `idle`, `walk`, `shake`, `roll` |
| status | waiting for the render |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (written by `../prompts.py`; never changed once an image is made from it):

> A young capybara, sandy brown, barrel-shaped with a big square muzzle, small round ears, short legs and no tail, on a flat muddy bank at the edge of a mangrove, the roots and trunks well behind it. Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left, in a relaxed standing pose: head level and looking ahead, all four legs straight and a little apart, every foot on the ground and in view, its tail in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground or grass, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Made from the cutout and the render, to [SPEC.md](../SPEC.md) section 3: 0.27 m long, one skinned mesh of at most 8,000 triangles and 1 MB,
one embedded texture (1024 at most), the named skeleton (`Root`, `Body`, `Chest`, `Neck`, `Head`, `Tail1`..., `LegFL`/`ShinFL`/`FootFL`
and the other three legs), skin weights, and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
