# Anvil Head (`anvil-head`)

Real size, not a tabletop species. The clean step scales the longest side of the mesh to the size below.

| | |
| --- | --- |
| size | **12.3 m** longest side |
| clips | `idle`, `walk` |
| status | new |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt`:

> An original two-legged hunter the size of a large tyrannosaur, a deep block of a head held up and paler than the dark body, tiny arms, a heavy tail held out, mottled brown hide, on a dry open plain. Natural wildlife photograph, realistic proportions. Camera at eye level and very far away, as if spotted from a road across open country, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. The animal stands still, side-on, facing left: its chest is raised, the block head is up, both feet are on the ground, and the tail is straight out. It fills about a third of the frame's width, with a low horizon, a pale plain sky behind it and generous empty space on every side, so its whole outline reads as a clean, high-contrast silhouette at a glance; nothing overlaps it and nothing in front of it. A little atmospheric haze between the camera and the animal shows the distance and its huge size. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the animal. Landscape frame, 16:9, 1280x720. No people, no vehicles, no roads, no other animals, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The animal alone from `full.jpg`, on transparency: no shadow, no ground, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Made from the cutout and the render. Longest side 12.3 m. Clips `idle`, `walk`, in place.
