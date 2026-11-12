"""Tricks: what a creature does when it is asked, like a dog that sits.

tricks.json names every trick once: its id and the phrases a player might say for it. An archetype's `TRICKS` lists
the ones its body can do and its `build` animates them with `b.trick(...)`, a one-shot clip named by the trick's id.
A trick the archetype does not animate is a behaviour, written in tricks.json as the commands to run (`do`): coming
over, staying, speaking, hiding. A species knows the `basics`, the first few of its archetype's (how many is its
rarity's `tricks`), or exactly the list its definition gives; a legendary adds a `signature` of its own.

In a creature's document every trick is an event named by its id: the actor's `on.<id>` handler does it, the header's
`tricks` and the mind's canned rules only `emit` it. Handlers are part of the actor, so they survive a TV renaming
the creature's state and ids, and they cost no tokens. Nothing here tells a player what the tricks are: the catalog
does not list them and the persona keeps them secret.
"""
import re

PHRASE = re.compile(r"^[a-z]+( [a-z]+)*$")
RESERVED = ("idle", "move", "swim", "walk", "fly", "tap", "near", "far", "spoken", "appear", "disappear", "animationEnd", "soundEnd", "arrived", "timer")
VERBS = ("play", "sound", "stopSound", "say", "moveTo", "lookAt", "stop", "wait", "emit", "behave")      # ActorCommand.verbs
MOTES = ("burst", "swirl", "gather", "rise", "fall")
SIGNATURE_KEYS = {"id", "phrases", "move", "motes"}


def phrase_faults(where, phrases):
    faults = []
    if not isinstance(phrases, list) or not 4 <= len(phrases) <= 7: return ["%s needs four to seven phrases" % where]
    for phrase in phrases:
        if not isinstance(phrase, str) or not PHRASE.match(phrase): faults.append("%s: the phrase %r must be lower-case words with single spaces and no punctuation" % (where, phrase))
    if len(set(phrases)) != len(phrases): faults.append("%s lists a phrase twice" % where)
    return faults


def command_faults(where, steps, meanings):
    """What is wrong with a list of actor commands."""
    faults = []
    if not isinstance(steps, list) or not steps: return ["%s needs commands to run" % where]
    for step in steps:
        verbs = [v for v in step if v in VERBS] if isinstance(step, dict) else []
        if len(verbs) != 1 or len(step) != 1: faults.append("%s: %r is not one actor command (%s)" % (where, step, ", ".join(VERBS)))
        elif verbs[0] == "sound" and step["sound"] not in meanings: faults.append("%s: plays the sound %r; the sounds are %s" % (where, step["sound"], ", ".join(meanings)))
    return faults


def table_faults(table, meanings):
    """What is wrong with tricks.json."""
    faults, tricks = [], table.get("tricks", {})
    for trick_id, entry in tricks.items():
        where = "the trick %s" % trick_id
        if not re.match(r"^[a-z]+$", trick_id) or trick_id in RESERVED: faults.append("%s: an id is lower-case letters and not one of JsonScene's events or clips (%s)" % (where, ", ".join(RESERVED)))
        faults += phrase_faults(where, entry.get("phrases"))
        if "do" in entry: faults += command_faults(where, entry["do"], meanings)
        if entry.get("sound", "call") not in meanings: faults.append("%s: its sound must be one of %s" % (where, ", ".join(meanings)))
    for trick_id in table.get("basics", []):
        if "do" not in tricks.get(trick_id, {}): faults.append("the basic trick %s needs a `do`, since not every archetype animates it" % trick_id)
    return faults


def known(table, d, archetype, rarity):
    """The ids of the tricks a species knows, in the order they are tried: its definition's list, or the basics and
    the first of its archetype's; then its signature."""
    if "tricks" in d: ids = list(d["tricks"])
    else:
        ids = list(table["basics"])
        ids += [t for t in archetype.TRICKS if t not in ids][:int(rarity.get("tricks", 0))]
    if isinstance(d.get("signature"), dict) and d["signature"].get("id"): ids.append(d["signature"]["id"])
    return ids


def phrases(table, d, trick_id):
    signature = d.get("signature") or {}
    return list(signature["phrases"]) if signature.get("id") == trick_id else list(table["tricks"][trick_id]["phrases"])


def species_faults(table, d, archetype, rarity):
    """What is wrong with a definition's tricks."""
    faults, signature = [], d.get("signature")
    if "tricks" in d:
        if not isinstance(d["tricks"], list) or not d["tricks"] or len(set(d["tricks"])) != len(d["tricks"]): return ["tricks must be a list of different trick ids"]
        for trick_id in d["tricks"]:
            if trick_id not in table["tricks"]: faults.append("unknown trick %r (tricks.json has %s)" % (trick_id, ", ".join(table["tricks"])))
            elif trick_id not in archetype.TRICKS and "do" not in table["tricks"][trick_id]: faults.append("the %s archetype cannot do the trick %s (it can do %s)" % (d["archetype"], trick_id, ", ".join(archetype.TRICKS)))
    if signature is not None:
        if not rarity.get("signature"): faults.append("only a rarity with `signature` (a legendary) has a signature trick")
        if not isinstance(signature, dict) or set(signature) != SIGNATURE_KEYS: return faults + ["signature needs id, phrases, move and motes"]
        if not isinstance(signature["id"], str) or not re.match(r"^[a-z]+$", signature["id"]) or signature["id"] in RESERVED or signature["id"] in table["tricks"]:
            faults.append("signature.id must be lower-case letters and not the id of an ordinary trick")
        faults += phrase_faults("signature", signature["phrases"])
        if signature["move"] not in archetype.TRICKS: faults.append("signature.move must be a trick the %s archetype animates (%s)" % (d["archetype"], ", ".join(archetype.TRICKS)))
        if signature["motes"] not in MOTES: faults.append("signature.motes is one of %s" % ", ".join(MOTES))
    elif rarity.get("signature"): faults.append("a %s species needs a signature trick of its own" % d["rarity"])
    if faults: return faults
    ids = known(table, d, archetype, rarity)
    if not ids: return ["knows no tricks"]
    said = {trick_id: phrases(table, d, trick_id) for trick_id in ids}
    for a in ids:
        for b in ids:
            if a == b: continue
            for phrase in said[a]:
                inside = [other for other in said[b] if phrase in other]
                if inside: faults.append("the phrase %r of the trick %s is inside %r of the trick %s, so asking for one could get the other" % (phrase, a, inside[0], b))
    return faults


def handler(table, d, trick_id, made):
    """The commands of the actor's `on.<trick>` handler; None when nothing can do the trick."""
    signature = d.get("signature") or {}
    if trick_id in made:
        seconds = round(made[trick_id], 2)
        if signature.get("id") == trick_id:
            return [{"behave": "idle"}, {"lookAt": "user"}, {"sound": "call"}, {"play": trick_id}, {"wait": seconds}, {"sound": "content"}, {"behave": "none"}]
        return [{"behave": "idle"}, {"lookAt": "user"}, {"sound": table["tricks"][trick_id].get("sound", "call")}, {"play": trick_id}, {"wait": seconds}, {"behave": "none"}]
    steps = table["tricks"].get(trick_id, {}).get("do")
    return [dict(step) for step in steps] if steps else None


def match(said):
    """The expression a canned rule tests against "<event> <heard>" to hear any of the phrases `said`."""
    return "^spoken\\b.*\\b(%s)\\b" % "|".join(sorted(said, key=lambda p: (-len(p), p)))


def header(table, d, ids):
    """`_ui.tricks`: what to listen for and what to run, with nothing but the document."""
    return [{"id": trick_id, "phrases": phrases(table, d, trick_id), "do": [{"emit": trick_id}]} for trick_id in ids]


def canned(table, d, ids):
    """Canned rules that do a trick when its phrase is heard and no model answers."""
    return [{"match": match(phrases(table, d, trick_id)), "do": [{"emit": trick_id}]} for trick_id in ids]
