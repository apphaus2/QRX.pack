# Giant Sequoia (`giant-sequoia`)

Real size, not a tabletop species. The clean step scales the longest side of the mesh to the size below. A plant stands and sways. It does not walk.

| | |
| --- | --- |
| size | **83.8 m** longest side |
| clips | `idle` |
| status | picture filed |

## Render prompt (`full.jpg`)

Kept word for word in `prompt.txt`:

> A giant sequoia, an enormously tall straight trunk of deep red-brown fibrous bark, a broad flared base, a tall bare trunk for most of its height with the first branches very high up, and a narrow even rounded crown of dark green foliage that is high and symmetrical, not lopsided or low, on a flat open meadow, low forested hills far behind it. Natural landscape photograph, realistic proportions. Camera at eye level and very far away, as if spotted from a road across open country, a near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. A single plant standing alone, seen side-on, its whole shape from the ground to its highest point in view, its base and roots meeting the ground in view, leaning or reaching toward the left. It fills about a third of the frame's width, with a low horizon, a pale plain sky behind it and generous empty space on every side, so its whole outline reads as a clean, high-contrast silhouette at a glance; nothing overlaps it and nothing in front of it. A little atmospheric haze between the camera and the plant shows the distance and its huge size. Soft, even daylight from an overcast sky, no hard shadows, no rim light. Sharp focus on the plant. Landscape frame, 16:9, 1280x720. No people, no animals, no vehicles, no roads, no buildings, no other trees, no text, no logos, no frame, no watermark.

## Cutout (`cutout.png`)

The plant alone from `full.jpg`, on transparency: no shadow, no ground, at least 16 pixels of margin, nothing touching the edge.

## Rigged mesh (`mesh.glb`)

Made from the cutout and the picture. Longest side 83.8 m. Clip `idle`, in place. The index still draws 32.5 by 83.8 by 32.5 m.
