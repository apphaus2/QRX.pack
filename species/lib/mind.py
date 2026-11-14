"""A creature's mind: what lets it be talked to (JsonMind, part of JsonScene).

A definition's `prompt` is the species speaking in the first person, with {tokens} that the apps fill in from one
creature's life information: {name}, {age}, {home} (the phrase of the biome it was met in, from biomes.json) and
{temperament} (its nature, one of life.json's) and {language} (the language the player talks to it in, by its English
name: "German"; an app that knows no language fills the header's default, "English").
The pipeline turns it into the actor's `mind`. The `persona` (the front of the system prompt) is the prompt, then
the species' speech register in plain words, then the closing lines and the rule about tricks that every creature
shares (how its nature shows, what it is, that its tricks are secret); the senses, tools, budget, triggers and canned rules come from mind.json, once for all species. A definition
may name its register (`speech`) and, rarely, give a `mind` object whose keys replace the shared ones.

What JsonMind does with it, which the choices in mind.json follow (JsonScene's ActorSimulation and MindSession):

- An event runs the actor's own `on` handler first and then wakes the mind if the event is one of its `triggers`.
  The handler always runs and costs nothing: it is where the tap behaviour, the tap and near sounds and every trick
  live. Only the mind can spend tokens.
- A mind that wakes goes to the model whenever a provider is attached, the budget has room and the cooldown has
  passed; there is no way to say "this trigger is canned only". So the only triggers are the player's own acts,
  `spoken` and `tap`. `near`, `far`, `timer` and everything else never reach the mind at all.
- The canned rules answer when there is no provider, when the provider fails (no key set) and when the budget is
  spent. They do not answer during the cooldown: then the mind does nothing, and only the handler is seen and heard.
- A canned rule is matched, without regard to case, against "<event> <heard text>": "tap ", "spoken roll over".
  The first rule that matches is the answer; nothing is chosen at random.
- A mind's commands, canned ones too, are dropped unless their verb is in `tools`. `behave` and `moveTo` from a
  mind replace the actor's behaviour list until another `behave`, which would switch the tap reaction off for good,
  and `set` could leave a state key stuck: none of the three is allowed. A canned rule does a trick by `emit`,
  which runs the actor's own handler for it.
- `budget.perTurn` is two things at once: a turn whose prompt is estimated above it never reaches the model (the
  canned rules answer instead), and it is the most the model may write back. The prompt grows with the history
  (6 turns), so perTurn has to cover the system text and a full history; `turn_estimate` is that sum.
- `say` is shown as a bubble and read aloud by the phone. A creature with no model behind it never says a word:
  no canned rule may `say`.
"""
import re

TOKEN = re.compile(r"\{([a-z]+)\}")
TOOLS = ("say", "sound", "lookAt", "play", "emit")       # what a mind here may do; see above for why not the rest
TRIGGERS = ("spoken", "tap")                             # the player did something to this creature
MIND_KEYS = ("senses", "tools", "budget", "triggers", "canned")
SENSES = ("userDistance", "userLooking", "timeOfDay", "state", "actors", "lastEvent")
HISTORY_TURNS = 6                        # MindSession.historyLimit
HISTORY_TURN_TOKENS = 60                 # one remembered turn: what was heard and what was answered
EVENT_TOKENS = 60                        # the turn's own event, a spoken sentence and the senses
LIFE_SLACK = 60                          # characters a life's name, age and home may add over the bare tokens
MAX_BUDGET = {"tokens": 12000, "perTurn": 1024}     # TokenLibMindProvider never asks for more than 1024 a turn
MIN_COOLDOWN = 5
VERBS = ("play", "sound", "stopSound", "say", "moveTo", "lookAt", "stop", "wait", "emit", "behave")      # ActorCommand.verbs


def tokens_in(text):
    """The token names in `text`, in order of first use."""
    seen = []
    for name in TOKEN.findall(text):
        if name not in seen: seen.append(name)
    return seen


def token_faults(text, known):
    """What is wrong with the braces and tokens in `text`."""
    faults = []
    if "{" in TOKEN.sub("", text) or "}" in TOKEN.sub("", text): faults.append("has a brace that is not part of a {token} (a token is { + lower-case letters + })")
    unknown = [name for name in tokens_in(text) if name not in known]
    if unknown: faults.append("uses the unknown token%s %s (known: %s)" % ("" if len(unknown) == 1 else "s", ", ".join("{%s}" % n for n in unknown), ", ".join("{%s}" % n for n in known)))
    return faults


def known_tokens(shared):
    """name (the creature's own), whatever mind.json gives a default for (age), home (where it was met) and
    temperament (its nature)."""
    return ["name"] + list(shared["tokens"]) + ["home", "temperament"]


def temperament(shared, d):
    """A species' typical nature: its definition's, or its archetype's."""
    return d.get("temperament", shared["temperaments"].get(d["archetype"]))


def homes(d, biomes):
    """The `home` phrase of every biome a species is found in, by biome id: what {home} reads as there."""
    return {biome: biomes[biome]["home"] for biome in d["biomes"]}


def header_tokens(shared, d, biomes):
    """What each token reads as for a creature with no life information: a copy of the template, at home."""
    return dict({"name": d["name"]}, **shared["tokens"], home=biomes[d["biomes"][0]]["home"], temperament=temperament(shared, d))


def register(d, rarity):
    """How a species speaks: its definition's `speech`, or its rarity's."""
    return d.get("speech", rarity.get("speech"))


def persona(shared, d, speech):
    return " ".join(part.strip() for part in (d["prompt"], shared["registers"][speech], shared["nature"], shared["closing"], shared["language"], shared["secret"]))


def build(shared, d, speech, trick_rules):
    """The `mind` of a definition's actor. `trick_rules` are the canned rules that hear its tricks; they come first."""
    mind = {"persona": persona(shared, d, speech)}
    for key in ("senses", "tools", "budget", "triggers"):
        value = shared["mind"][key]
        mind[key] = dict(value) if isinstance(value, dict) else list(value)
    mind["canned"] = list(trick_rules) + [dict(rule) for rule in shared["canned"]]
    for key, value in d.get("mind", {}).items(): mind[key] = value
    return mind


def system_text(name, mind, animations, sounds, behaviours):
    """The system prompt JsonMind sends (MindPrompt.systemText), to know what a turn costs."""
    lines = {"say": '  {"say": "short text to speak"}', "play": '  {"play": "animation name"}', "sound": '  {"sound": "sound name"}',
             "moveTo": '  {"moveTo": "user"} or {"moveTo": [x, y, z]}', "lookAt": '  {"lookAt": "user"}',
             "behave": '  {"behave": "wander" | "approach" | "flee" | "follow" | "idle"}', "set": '  {"set": {"stateKey": value}}',
             "stop": '  {"stop": true}', "wait": '  {"wait": seconds}'}
    text = "You are %s, a character in an augmented reality scene.\n%s\n" % (name, mind["persona"])
    text += "\nReply with ONLY a JSON array of commands, nothing else. Allowed commands:\n"
    text += "".join(lines.get(tool, '  {"%s": ...}' % tool) + "\n" for tool in mind["tools"])
    text += "Animations: %s\nSounds: %s\nBehaviors: %s\n" % (", ".join(sorted(animations)), ", ".join(sorted(sounds)), ", ".join(sorted(set(behaviours) | {"idle"})))
    return text + "Keep replies short: at most 3 commands and one sentence of speech."


def turn_estimate(name, mind, animations, sounds, behaviours):
    """The most tokens JsonMind will estimate for one turn's prompt, by its own rule of four characters a token:
    the system text with a life filled in, a full history and the event."""
    return (len(system_text(name, mind, animations, sounds, behaviours).encode("utf-8")) + LIFE_SLACK + 3) // 4 + HISTORY_TURNS * HISTORY_TURN_TOKENS + EVENT_TOKENS


def rule_faults(rules, tools, meanings, events=()):
    """What is wrong with a list of canned rules: (faults, the compiled expressions)."""
    faults, compiled = [], []
    if not isinstance(rules, list) or not rules: return ["canned needs at least one rule"], []
    for i, rule in enumerate(rules):
        steps = rule.get("do") if isinstance(rule, dict) else None
        steps = [steps] if isinstance(steps, dict) else steps
        if not isinstance(rule, dict) or not isinstance(rule.get("match"), str) or not isinstance(steps, list) or not steps:
            faults.append("canned rule %d needs a match and something to do" % (i + 1)); continue
        try: compiled.append(re.compile(rule["match"], re.IGNORECASE))
        except re.error as error: faults.append("canned rule %d: its match is not a regular expression: %s" % (i + 1, error))
        for step in steps:
            verbs = [v for v in step if v in VERBS] if isinstance(step, dict) else []
            if len(verbs) != 1 or len(step) != 1: faults.append("canned rule %d: %r is not one command" % (i + 1, step)); continue
            verb = verbs[0]
            if verb == "say": faults.append("canned rule %d says %r: with no model behind it a creature makes sounds, never words" % (i + 1, step["say"]))
            elif verb not in tools: faults.append("canned rule %d: %s is not one of the mind's tools, so JsonMind would drop it" % (i + 1, verb))
            if verb == "sound" and step["sound"] not in meanings: faults.append("canned rule %d plays the sound %r; the sounds are %s" % (i + 1, step["sound"], ", ".join(meanings)))
            if verb == "emit" and events and step["emit"] not in events: faults.append("canned rule %d emits %r, which no handler of the actor answers" % (i + 1, step["emit"]))
    return faults, compiled


def mind_faults(mind, meanings, events=()):
    """What is wrong with a mind's working parts (everything but its persona)."""
    faults = []
    tools, triggers, budget = mind.get("tools"), mind.get("triggers"), mind.get("budget")
    if not isinstance(tools, list) or not tools or any(t not in TOOLS for t in tools) or "say" not in tools:
        faults.append("tools must include say and may add only %s: behave, moveTo and set would undo or outlast the tap behaviour" % ", ".join(TOOLS))
        tools = []
    if not isinstance(triggers, list) or not triggers or any(t not in TRIGGERS for t in triggers):
        faults.append("triggers may be %s: a mind thinks only when the player speaks to the creature or taps it, never on a timer or because someone is near" % " and ".join(TRIGGERS))
        triggers = []
    if not isinstance(mind.get("senses"), list) or any(s not in SENSES for s in mind["senses"]): faults.append("senses may be %s" % ", ".join(SENSES))
    whole = lambda v: isinstance(v, int) and not isinstance(v, bool)
    if not isinstance(budget, dict) or set(budget) != {"tokens", "perTurn", "cooldown"}: faults.append("budget needs tokens, perTurn and cooldown")
    else:
        if not whole(budget["tokens"]) or not 0 < budget["tokens"] <= MAX_BUDGET["tokens"]: faults.append("budget.tokens must be a whole number up to %d" % MAX_BUDGET["tokens"])
        if not whole(budget["perTurn"]) or not 0 < budget["perTurn"] <= MAX_BUDGET["perTurn"]: faults.append("budget.perTurn must be a whole number up to %d" % MAX_BUDGET["perTurn"])
        elif whole(budget["tokens"]) and budget["perTurn"] > budget["tokens"]: faults.append("budget.perTurn is more than budget.tokens")
        if not isinstance(budget["cooldown"], (int, float)) or isinstance(budget["cooldown"], bool) or budget["cooldown"] < MIN_COOLDOWN: faults.append("budget.cooldown must be at least %d seconds" % MIN_COOLDOWN)
    found, compiled = rule_faults(mind.get("canned"), tools, meanings, events)
    faults += found
    for trigger in triggers:
        if compiled and not any(r.search(trigger + " ") for r in compiled): faults.append("no canned rule answers %s, so the creature would do nothing without a model" % trigger)
    return faults


def shared_faults(shared, tempers, meanings):
    """What is wrong with mind.json."""
    faults = []
    tokens = shared.get("tokens")
    if not isinstance(tokens, dict) or any(not TOKEN.fullmatch("{%s}" % k) or not isinstance(v, str) or not v.strip() or "{" in v or "}" in v for k, v in tokens.items()):
        return ["tokens must map lower-case token names to what they read as with no life information"]
    if "age" not in tokens: faults.append("tokens needs a default for age")
    if set(tokens) & {"name", "home", "temperament"}: faults.append("tokens must not give name, home or temperament a default: they are each species' own name, its home biome's phrase and its typical nature")
    limits = shared.get("prompt", {})
    if not (isinstance(limits.get("min"), int) and isinstance(limits.get("max"), int) and 0 < limits["min"] < limits["max"]): faults.append("prompt needs whole min < max characters")
    plain = lambda text: isinstance(text, str) and text.strip() and "\n" not in text and "{" not in text and "}" not in text
    registers = shared.get("registers")
    if not isinstance(registers, dict) or not registers or any(not plain(text) or not re.match(r"^I\b", text) for text in registers.values()):
        faults.append("registers must map each speech register to one line, in the first person, that tells the creature how to speak")
    for key in ("nature", "closing", "secret"):
        if not plain(shared.get(key)): faults.append("%s must be one line of text with no braces" % key)
    line = shared.get("language")
    if not isinstance(line, str) or not line.strip() or "\n" in line or tokens_in(line) != ["language"] or token_faults(line, ["language"]):
        faults.append("language must be one line that uses the token {language} and no other")
    if "language" not in tokens: faults.append("tokens needs a default for language: what an app that knows no language fills in")
    table = shared.get("on", {})
    for event in ("tap", "near"):
        if not isinstance(table.get(event), dict) or any(table[event].get(temper) not in meanings for temper in tempers): faults.append("on.%s needs a sound (%s) for each temper (%s)" % (event, ", ".join(meanings), ", ".join(tempers)))
    if not isinstance(shared.get("mind"), dict): faults.append("mind needs senses, tools, budget and triggers")
    elif not faults: faults += mind_faults(dict(shared["mind"], canned=shared.get("canned")), meanings)
    return faults
