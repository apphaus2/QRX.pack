# Tilehop (`tilehop`)

Boop: A fuzzy teal ball on two big feet, with a long tube nose. Every paving tile it lands on glows.

| | |
| --- | --- |
| found in | town (home: Town) |
| rarity | rare |
| habitat | ground (walks) |
| size | **0.07 m** long |
| clips | `idle`, `walk`, `jump`, `flip`, `puff` |
| status | render made; cutout, mesh and rig by MeshTool |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (never changed once an image is made from it):

> A small round ball-shaped fuzzy creature the size of a tennis ball, a soft teal-blue body, only two legs: two short sturdy legs under the ball with big flat rounded feet, like a little bipedal bird. A long tube-shaped nose sticks straight forward from its face, about as long as its body is wide, open at the tip. Two large round white eyes with black pupils. Standing on a single square paving tile that glows a soft warm yellow under its feet, on the flat paving stones of a quiet back street, a low old brick wall well behind it. A cheerful retro-arcade hopper creature, made real. Natural wildlife photograph, realistic proportions, a believable living creature. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left, in a relaxed standing pose: head level and looking ahead, both legs straight and a little apart, both feet on the ground and in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

To [SPEC.md](../SPEC.md) section 3 where it fits this body (frog): 0.07 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
