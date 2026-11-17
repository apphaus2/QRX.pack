# The request to Grok

Paste the block below to Grok, then give it one creature's `prompt.md` at a time (start with `street-terrier`).
Take what it returns in with `python3 species/art/intake.py <id> --full ... --cutout ... --mesh ... --tool "Grok, <date>"`.

```text
You are making game-ready animal models for QRay, a children's mixed-reality game on Meta Quest 3, iPhone and
Android. Each animal sits on a table within arm's reach of a seated player, walks about, and does a few tricks when
asked. I will give you one creature brief at a time. For each, make and send me three files.

1. full.jpg: a photographic render of the animal, made from the brief's render prompt exactly as written. Side-on,
   facing left, eye level, far away with a long lens, the animal small in the frame (about a fifth of its width) with
   empty space all round, standing still with all four feet on the ground and in view, tail in view, nothing in front
   of it. Soft overcast daylight. Landscape 3:2, at least 1536 px wide. No people, other animals, text or watermark.

2. cutout.png: the same animal cut out of full.jpg onto full transparency. No shadow, no ground, no grass between its
   feet. Solid alpha inside the body, soft only at the fur's edge. At least 16 px of empty margin; nothing touches the
   edge.

3. mesh.glb: a rigged, animated, textured 3D model of that animal, made from the render and the cutout so it looks
   like them, every marking included.
   - glTF 2.0 binary, everything embedded (no external files). Metres, +Y up, the head pointing along +Z, the
     animal's left along +X, the origin on the ground under the middle of the body. Real size: the longest side
     (nose to tail or rump) is the brief's size in metres, and it is never taller than 0.15 m in any clip.
   - One continuous skinned mesh (eyes may be separate, parented to the head bone). At most 8,000 triangles. One
     base-colour texture, at most 1024 x 1024 (512 is fine), embedded; PBR metallic-roughness, metallic 0, roughness
     about 0.8. No vertex colours. The whole file 5 MB at most.
   - One skin. Bones with exactly these names (more are welcome: ears, jaw, toes, more tail):
     Root (on the ground, never moves) > Body (hips and spine) > Chest (shoulders) > Neck > Head;
     Body > Tail1 > Tail2 > Tail3 (fewer for a stub tail);
     Chest > LegFL > ShinFL > FootFL and Chest > LegFR > ShinFR > FootFR (front legs: shoulder, elbow, paw);
     Body > LegBL > ShinBL > FootBL and Body > LegBR > ShinBR > FootBR (back legs: hip, knee, paw or hoof).
     Smooth weights, at most 4 bones per vertex; knees and elbows bend cleanly with no collapse or tearing. The rest
     pose is the render's standing pose.
   - Animation clips with exactly these names, all in place (no root motion; Root stays still):
     idle   loop, about 3 s: breathing, looking about, the tail and ears moving a little.
     walk   loop, one stride, 0.6 to 1.0 s: a walk on the spot, diagonal legs together, each foot lifting as it comes
            forward, a slight nod of the head.
     and one clip for each cue the brief lists, played once, 0.8 to 3 s, starting and ending exactly in the rest pose:
     shake  shakes itself like a wet dog, head to tail.     roll   rolls onto its back and right over to its feet.
     bow    play bow: front down, rump up, tail wagging.    jump   jumps straight up, legs tucked, and lands.
     spin   turns a full circle on the spot.                dead   lies down on its side, still, then gets up.
     wave   lifts one front paw and waves it.              dance  a happy bouncing dance on the spot.

Look: a realistic young animal, natural colours, friendly. Nothing frightening: this is for children.

When you send the files, also tell me: the triangle count, the texture size, the file size, the bones and the clips
in the .glb, and anything in the brief you could not do. If you cannot make a rigged mesh, still send full.jpg and
cutout.png and say so.
```

## Then each creature

After the block, send the creature's brief, for example:

```text
Creature brief: street-terrier
<paste species/art/street-terrier/prompt.md here>
```
