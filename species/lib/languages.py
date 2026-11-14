"""Cues in other languages: the phrases that ask a creature for each cue, and how a recogniser in that language may
write each name of the pack.

English is tricks.json (and each legendary's `signature`), as it always was. Every other language QRay listens in
has a table here, `languages/<code>.json`, keyed by the same cue ids: `cues` (every ordinary cue and every
signature, four to eight phrases each) and, for the languages written in another script, `names` (each name of
life.json's pool and each species' template name, as the recogniser most likely writes it). The tables were
machine-written and carry `"checked": false` until a native speaker has read them.

A phrase is written once, lower case, as the recogniser writes the language (Simplified Chinese characters,
Japanese kanji and kana, Hangul, Cyrillic). The matcher does the rest, and `tokens` here is the same reading as the
apps' shared core (QRX's core/qrx-core/src/hearing.rs, `words_in`), so the checks below hold for what the apps hear:

- case is folded, and so are the Latin accents and ligatures (é is e, ß is ss, œ is oe), ё (е) and full-width
  Latin letters; katakana reads as hiragana;
- punctuation, apostrophes and hyphens cut words ("cache-toi" is "cache", "toi");
- a Chinese, Japanese or Korean character is a word of its own, so a phrase is found inside what was said whatever
  the spacing: "이리 와" and "이리와" are the same phrase. That is why such a phrase needs two characters or more.

A document carries the tables in `_ui.cues` (see header below); the English `_ui.tricks` is written beside it,
unchanged, for the apps that read only that.
"""
import json, os, re, unicodedata

CODES = ("de", "es", "fr", "it", "pt", "ru", "zh", "ja", "ko")       # QRay's SpeechLanguage, English aside
SCRIPTS = {"ru": "Cyrillic", "zh": "Han", "ja": "Japanese", "ko": "Hangul"}   # the languages whose names need a written form
UNIT = {"zh", "ja", "ko"}                                                     # no spaces between words
KEYS = {"language", "checked", "about", "cues", "names"}
FOLD = {}
for letters, plain in (("àáâãäåāăą", "a"), ("çćč", "c"), ("ďđ", "d"), ("èéêëēėęě", "e"), ("ğ", "g"), ("ìíîïīį", "i"), ("ł", "l"),
                       ("ñńň", "n"), ("òóôõöøōő", "o"), ("ŕř", "r"), ("śšş", "s"), ("ťţ", "t"), ("ùúûüūůű", "u"), ("ýÿ", "y"),
                       ("źżž", "z"), ("ё", "е")):
    for letter in letters: FOLD[letter] = plain
FOLD.update({"ß": "ss", "œ": "oe", "æ": "ae"})
PHRASE_MARKS = set(" '’-")


def is_word(c):
    return unicodedata.category(c)[0] in "LN"


def is_unit(c):
    """A character that is a word by itself: a Han ideograph, kana, a Hangul syllable."""
    n = ord(c)
    return 0x3005 <= n <= 0x3007 or 0x3040 <= n <= 0x30FF or 0x3400 <= n <= 0x4DBF or 0x4E00 <= n <= 0x9FFF or 0xF900 <= n <= 0xFAFF or 0xAC00 <= n <= 0xD7A3


def fold(c):
    """One character as the matcher reads it: full-width Latin as Latin, lower case, accents off, katakana as hiragana."""
    n = ord(c)
    if 0xFF01 <= n <= 0xFF5E: c = chr(n - 0xFEE0)
    out = []
    for lower in c.lower():
        lower = FOLD.get(lower, lower)
        out += [chr(ord(ch) - 0x60) if 0x30A1 <= ord(ch) <= 0x30F6 else ch for ch in lower]
    return "".join(out)


def tokens(text):
    """The words of `text` as the matcher reads them in a language other than English."""
    out, word = [], ""
    for c in "".join(fold(c) for c in text):
        if is_word(c) and is_unit(c):
            if word: out.append(word); word = ""
            out.append(c)
        elif is_word(c): word += c
        elif word: out.append(word); word = ""
    if word: out.append(word)
    return out


def inside(a, b):
    """Whether the words `a` stand together inside the words `b`."""
    return len(a) <= len(b) and any(b[i:i + len(a)] == a for i in range(len(b) - len(a) + 1))


def read(here):
    """Every language's table, by code; a missing one is a fault for `faults`."""
    tables = {}
    for code in CODES:
        path = os.path.join(here, "languages", code + ".json")
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f: tables[code] = json.load(f)
    return tables


def phrase_faults(where, code, phrases):
    faults = []
    if not isinstance(phrases, list) or not 4 <= len(phrases) <= 8: return ["%s needs four to eight phrases" % where]
    seen = []
    for phrase in phrases:
        if not isinstance(phrase, str) or phrase != phrase.strip() or "  " in phrase or phrase != phrase.lower() or any(not is_word(c) and c not in PHRASE_MARKS for c in phrase):
            faults.append("%s: the phrase %r must be lower case, letters with single spaces, apostrophes or hyphens, no other punctuation" % (where, phrase)); continue
        if code in ("zh", "ja") and " " in phrase: faults.append("%s: the phrase %r has a space; Chinese and Japanese are written without" % (where, phrase))
        words = tokens(phrase)
        if code in UNIT and len(words) < 2: faults.append("%s: the phrase %r is one character, which would be found inside other words" % (where, phrase))
        if words in seen: faults.append("%s lists %r twice (as the matcher reads it)" % (where, phrase))
        seen.append(words)
    return faults


def table_faults(tables, cue_ids, names):
    """What is wrong with the language tables: `cue_ids` every cue a document can carry, `names` every name of the pack."""
    faults = []
    for code in CODES:
        if code not in tables: faults.append("languages/%s.json: missing" % code); continue
        table, where = tables[code], "languages/%s.json" % code
        if set(table) - KEYS: faults.append("%s: unknown keys %s" % (where, ", ".join(sorted(set(table) - KEYS))))
        if table.get("language") != code: faults.append("%s: language must be %r" % (where, code))
        if not isinstance(table.get("checked"), bool): faults.append("%s: checked must be true once a native speaker has read it, false until then" % where)
        cues = table.get("cues", {})
        missing, extra = [c for c in cue_ids if c not in cues], [c for c in cues if c not in cue_ids]
        if missing: faults.append("%s: no phrases for %s" % (where, ", ".join(missing)))
        if extra: faults.append("%s: phrases for unknown cues %s" % (where, ", ".join(extra)))
        for cue, phrases in cues.items(): faults += phrase_faults("%s, the cue %s" % (where, cue), code, phrases)
        forms = table.get("names", {})
        if code in SCRIPTS and not isinstance(forms, dict): faults.append("%s: names maps each name of the pack to how it is written in %s" % (where, SCRIPTS[code]))
        for name, written in (forms.items() if isinstance(forms, dict) else []):
            if name not in names: faults.append("%s: names has %r, which is no name of the pack" % (where, name)); continue
            if not isinstance(written, list) or not written: faults.append("%s: names.%s needs one written form or more" % (where, name)); continue
            for form in written:
                if not isinstance(form, str) or form != form.strip() or not tokens(form): faults.append("%s: names.%s: %r is not a name" % (where, name, form))
                elif code in UNIT and len(tokens(form)) < 2: faults.append("%s: names.%s: %r is one character, which would be found inside other words" % (where, name, form))
    return faults


def phrases(tables, code, cue_id):
    return list(tables.get(code, {}).get("cues", {}).get(cue_id, []))


def species_faults(tables, ids):
    """In every language, no phrase of one cue a species knows may stand inside a phrase of another it knows."""
    faults = []
    for code in CODES:
        said = {cue: [tokens(p) for p in phrases(tables, code, cue)] for cue in ids}
        for a in ids:
            for b in ids:
                if a == b: continue
                for phrase in said[a]:
                    hit = next((other for other in said[b] if inside(phrase, other)), None)
                    if hit is not None:
                        faults.append("%s: the phrase %r of the cue %s is inside %r of the cue %s" % (code, " ".join(phrase), a, " ".join(hit), b))
    return faults


def header(tables, english_header):
    """`_ui.cues`: the English header's entries with each language's phrases under `languages`."""
    out = []
    for entry in english_header:
        languages = {code: phrases(tables, code, entry["id"]) for code in CODES if phrases(tables, code, entry["id"])}
        out.append({"id": entry["id"], "phrases": list(entry["phrases"]), "languages": languages, "do": [dict(step) for step in entry["do"]]})
    return out


def names_file(tables, names):
    """species/names.json: every name of the pack and its written forms by language (only where the table has one)."""
    out = {}
    for name in sorted(names):
        forms = {code: list(tables[code]["names"][name]) for code in CODES if name in tables.get(code, {}).get("names", {})}
        if forms: out[name] = forms
    return {
        "about": "How a speech recogniser listening in another language may write each name of the pack: the life.json pool and every species' template name. Built from species/languages/*.json by build.py; machine-written, not yet checked by native speakers. QRX's shared core carries a copy (core/qrx-core/data/spoken-names.json) to find a creature's name in what was said.",
        "version": 1,
        "languages": [code for code in CODES if tables.get(code, {}).get("names")],
        "names": out,
    }
