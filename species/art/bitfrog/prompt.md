# Bitfrog (`bitfrog`)

Byte: A frog built of little green blocks. It jumps in square steps and croaks a chiptune.

| | |
| --- | --- |
| found in | wetland (home: Marsh) |
| rarity | epic |
| habitat | ground (walks) |
| size | **0.09 m** long |
| clips | `idle`, `walk`, `jump`, `flip`, `puff`, `spin` |
| status | render made; cutout, mesh and rig by MeshTool |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (never changed once an image is made from it):

> A young frog whose whole body is built of small square blocks, like a voxel sculpture come to life, bright lime green with a darker green back and a pale yellow belly, two big square black eyes with a single white square highlight in each, blocky stepped legs, on a flat muddy bank at the edge of a reed marsh, the reeds well behind it. Natural wildlife photograph, realistic lighting, a believable living creature. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal sits still, side-on, facing left, in a relaxed sitting pose: head level and looking ahead, all four feet on the ground and in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

To [SPEC.md](../SPEC.md) section 3 where it fits this body (frog): 0.09 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
