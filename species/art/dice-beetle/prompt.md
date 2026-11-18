# Dice Beetle (`dice-beetle`)

Lucky: A beetle whose body is an ivory die with black pips. It tumbles face over face to see what it rolls.

| | |
| --- | --- |
| found in | town (home: Town) |
| rarity | uncommon |
| habitat | ground (walks) |
| size | **0.05 m** long |
| clips | `idle`, `walk`, `spin`, `dead` |
| status | render made; cutout, mesh and rig by MeshTool |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt` (never changed once an image is made from it):

> Side view of a small living beetle whose body is an ivory-white six-sided gaming die, a glossy cube with softly rounded edges, about 4 cm across. The side face we see shows five round black pips like a standard die, placed in the upper part of the face. Along the bottom edge of that side face there are exactly three black jointed beetle legs, one near the front corner, one in the middle and one near the back corner, each coming out of the side face and bending outward and down to the ground. The three far-side legs are mostly hidden behind the die, only their feet showing. Six legs in total. No legs come out of the front face or from under the die. A glossy black beetle head with two antennae is attached at the middle of the die's front face, halfway up, in profile, facing left. The die is held a little off the ground by its legs. On the flat paving stones of a quiet back street, a low old brick wall well behind it. Natural wildlife photograph, realistic proportions, a believable living creature. Camera at the animal's eye level and far away, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left: head level, all its legs on the ground and in view. It is small in the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame. No people, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, water or plants, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

To [SPEC.md](../SPEC.md) section 3 where it fits this body (beetle): 0.05 m long, one skinned mesh, one embedded texture,
and the clips above, in place, each cue starting and ending in the rest pose. It must look like the render and the cutout, every mark included.
