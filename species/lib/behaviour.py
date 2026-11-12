"""What a creature does, from its definition's `behaviour`: the behaviors, the tap handler and the state key the
creature documents carry. The three tempers are the pack's "tap and it runs from you" and two gentler ones.

    {"temper": "shy",     "distance": 1.6, "seconds": 3}    tapped, it keeps `distance` from the viewer for `seconds`
    {"temper": "curious", "distance": 0.5, "seconds": 4}    tapped, it comes to within `distance` of the viewer
    {"temper": "calm",    "seconds": 4}                     tapped, it stops where it is
    "watch": true                                           it turns to face the viewer whatever else it does
"""

TEMPERS = {
    "shy": ("scared", lambda d: {"type": "flee", "from": "user", "distance": d.get("distance", 1.6), "priority": 10, "when": "$scared"}),
    "curious": ("curious", lambda d: {"type": "approach", "target": "user", "stopAt": d.get("distance", 0.5), "priority": 10, "when": "$curious"}),
    "calm": ("still", lambda d: {"type": "idle", "priority": 10, "when": "$still"}),
}


def logic(behaviour, pause):
    """(state, behaviors, on) for an actor."""
    key, react = TEMPERS[behaviour.get("temper", "shy")]
    behaviors = [react(behaviour)]
    if behaviour.get("watch"): behaviors.append({"type": "lookAt", "target": "user", "priority": 1})
    behaviors.append({"type": "wander", "pause": list(pause)})
    on = {"tap": [{"set": {key: True}}, {"wait": behaviour.get("seconds", 3)}, {"set": {key: False}}]}
    return {key: False}, behaviors, on
