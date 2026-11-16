#!/usr/bin/env python3
"""Writes species/art/<id>/prompt.txt: what the image agent is asked to render for each creature, in TerraLib's
manner (its IMAGING.md, sections 3 and 6): the animal in its home habitat, small in the frame, side-on at eye level,
clearly apart from what is behind it, no people, no text, no other animals.

    python3 species/art/prompts.py            write the prompts that are missing
    python3 species/art/prompts.py --check    exit 1 if a creature listed below has no prompt.txt

A prompt is the record of how its image was made, so this never overwrites one: once an image has been made from a
prompt, that prompt is kept as it is. To change a prompt before anything was rendered from it, delete prompt.txt and
run this again.

The look of each animal is written here by hand from its definition (species/definitions/...), in words only:
the definition's colours and personality are for the procedural models and the mind, not for an image model.
"""
import argparse, glob, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SPECIES = os.path.dirname(HERE)

# Where each home biome is, as a setting: open ground near the animal so its feet show and the cutout has no soil
# to cut through; anything tall stays well behind it.
SETTINGS = {
    "town": "on the flat paving stones of a quiet back street, a low old brick wall well behind it",
    "farm": "on short trodden grass in a farmyard, a weathered wooden fence well behind it",
    "forest": "on a bare patch of leaf litter in a clearing of a temperate broadleaf forest, the trunks well behind it",
    "barren": "on flat pale rock on a dry mountain slope, boulders and scree well behind it",
    "snow": "on firm packed snow in an open snowfield, a few dark spruce trees far behind it",
    "meadow": "on a short-mown path through a summer meadow, the tall grass and flowers well behind it",
    "shrub": "on bare sandy ground in a clearing in dry heath, gorse and heather bushes well behind it",
    "wetland": "on a flat muddy bank at the edge of a reed marsh, the reeds well behind it",
    "mangrove": "on a flat muddy bank at the edge of a mangrove, the roots and trunks well behind it",
    "water": "on a flat pebbly riverbank, the water and the far bank well behind it",
}

# The animal, in words: a young one, its coat and markings, and the one or two things that make it itself.
LOOKS = {
    "alley-cat": "a young grey tabby cat with dark grey stripes, a cream chest, white socks on all four paws, green eyes, pointed ears and a long striped tail held up",
    "crag-kid": "a young goat kid with a sandy coat, a dark brown stripe along its back, short swept-back horns, a tiny beard, amber eyes and dark hooves",
    "dapple-calf": "a young calf, white with large chocolate-brown patches, two small horn buds, a pink muzzle, dark hooves and a thin tail with a brown tuft",
    "dapple-fawn": "a young red deer fawn, russet brown with rows of small cream spots on its back, a pale belly, large ears, long thin legs and dark hooves",
    "farmyard-piglet": "a young pink piglet with three or four grey patches, a flat round snout, floppy ears, small dark trotters and a curly tail",
    "frost-wolf-pup": "a young grey wolf pup, pale silver grey with a darker grey back, a white chest and belly, ice-blue eyes, big white paws, pointed ears and a bushy tail",
    "honeyglow-bear-cub": "a young brown bear cub, round and fluffy, dark brown with a honey-coloured muzzle and belly, small round ears and a short stub of a tail",
    "marsh-capybara": "a young capybara, sandy brown, barrel-shaped with a big square muzzle, small round ears, short legs and no tail",
    "meadow-cottontail": "a young wild rabbit, warm brown with a darker back, a cream belly, long upright ears and a round white cotton tail",
    "meadow-pony": "a young chestnut pony with a long flaxen mane and tail, a white blaze down its face, white socks on its legs and dark hooves",
    "meadow-sheepdog": "a young black and white border collie, black back and ears, white chest, white blaze and white paws, floppy ears and a long bushy tail",
    "moonlit-cat": "a young black cat, glossy black all over, with round golden-yellow eyes, pointed ears and a long thin tail held up",
    "red-squirrel": "a young red squirrel, russet orange with a cream belly, tufted ears and a big bushy tail curved up over its back",
    "ringtail-raccoon": "a young raccoon, grey with a black mask across its eyes, a pale muzzle, small round ears, dark hands and a bushy tail ringed black and grey",
    "river-otter": "a young river otter, long and low, glossy dark brown with a pale cream throat, tiny round ears, short legs and a thick tapering tail",
    "street-terrier": "a young scruffy terrier with a wiry tan coat, a dark brown saddle on its back, a cream muzzle and chest, white paws, folded ears and a long tail held up",
    "stripe-badger": "a young European badger, low and broad, grey above and black below, a white face with a black stripe through each eye, small white-tipped ears and short black legs",
    "woolly-lamb": "a young lamb with a thick cream fleece, a black face, black ears and four black legs",
}

SHOT = ("Natural wildlife photograph, realistic proportions. Camera at the animal's eye level and far away, a "
        "near-orthographic side view with a long lens: no wide angle, no low angle, no looking down. "
        "The animal stands still, side-on, facing left, in a relaxed standing pose: head level and looking ahead, all "
        "four legs straight and a little apart, every foot on the ground and in view, its tail in view. It is small in "
        "the frame, about a fifth of the frame's width, with generous empty space on every side, and clearly "
        "separated from everything behind it: nothing overlaps it. Soft, even daylight from an overcast sky, no hard "
        "shadows, no rim light. Sharp focus on the animal. Landscape frame, 3:2. "
        "No people, no other animals, no text, no logos, no frame, no watermark.")


def definitions():
    out = {}
    for path in glob.glob(os.path.join(SPECIES, "definitions", "*", "*.json")):
        with open(path, encoding="utf-8") as f: d = json.load(f)
        out[d["id"]] = d
    return out


def prompt(d):
    return "%s, %s. %s\n" % (LOOKS[d["id"]][0].upper() + LOOKS[d["id"]][1:], SETTINGS[d["biomes"][0]], SHOT)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--check", action="store_true", help="say which listed creatures have no prompt.txt; write nothing")
    args = parser.parse_args()
    defs, missing, wrote = definitions(), [], []
    unknown = sorted(set(LOOKS) - set(defs))
    if unknown: sys.exit("no definition for %s" % ", ".join(unknown))
    for creature in sorted(LOOKS):
        path = os.path.join(HERE, creature, "prompt.txt")
        if os.path.exists(path): continue
        if args.check: missing.append(creature); continue
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "x", encoding="utf-8") as f: f.write(prompt(defs[creature]))
        wrote.append(creature)
    if args.check:
        print("no prompt.txt: %s" % (", ".join(missing) or "none"))
        sys.exit(1 if missing else 0)
    print("wrote %d prompt(s)%s" % (len(wrote), (": " + ", ".join(wrote)) if wrote else ""))


if __name__ == "__main__":
    main()
