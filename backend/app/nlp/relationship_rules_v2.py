"""Rule-based relationship extraction, version 2: pair-scoped instead of sentence-scoped.

The legacy extractor (v1) labeled EVERY microbe-metabolite pair in a sentence
with whichever trigger word appeared ANYWHERE in it, so "L. reuteri reduced
TMAO, whereas E. coli produced acetate" yielded "L. reuteri produces TMAO",
and negation only halved the confidence. v2 reads the words linking each
specific pair:

1. Clauses: pairs are only formed inside one clause (split on ; whereas /
   while / but / although / however). A subject-initial microbe carries over
   into a following clause that has no microbe of its own ("X does not ferment
   A but degrades B").
2. Trigger: the relation verb is taken from the text BETWEEN the two mentions,
   choosing the trigger nearest to the metabolite. Passive voice ("B is
   produced by X"), source phrases ("LPS from E. coli") and nominal forms
   ("a butyrate producer", "butyrate-producing") are handled explicitly.
3. Substrate vs product: in "X converts A to B" / "X produces B from A",
   the linking word after the first metabolite (to/into vs from/via) decides
   whether the next metabolite is a product or a substrate. Coordinated
   metabolites ("A and B") share a relation; anything else is a distractor.
4. Scoped negation: a negation cue between the pair (or "neither/nor" just
   before the microbe) marks the relation as negated instead of asserted.
5. Subject check: if a different, non-coordinated microbe sits between the
   pair, the verb belongs to that closer microbe and the pair is skipped.
6. Hedging ("may", "suggest") lowers confidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.nlp.entity_extractor import Entity, extract_entities
from app.nlp.relationship_extractor import Relationship, _split_sentences

# Ordered by priority: earlier types win when two triggers overlap (e.g. "up-regulates").
TRIGGERS: list[tuple[str, str]] = [
    ("inhibits", r"down-?regulat\w*"),
    ("activates", r"up-?regulat\w*"),
    ("converts", r"convert\w*|transform\w*|decarboxylat\w*|bioconvert\w*|catalyz\w*|dehydroxylat\w*"),
    ("produces", r"produc\w*|secret\w*|synthesi[sz]\w*|generat\w*|excret\w*|releas\w*|yield\w*|source"),
    ("consumes", r"consum\w*|metaboli[sz]\w*|degrad\w*|utili[sz]\w*|ferment\w*|digest\w*|uptake|catabol\w*"
                 r"|exploit\w*|assimilat\w*"),
    ("inhibits", r"inhibit\w*|suppress\w*|block\w*|reduc\w*|decreas\w*|lower\w*|diminish\w*|attenuat\w*|impair\w*"),
    ("activates", r"increas\w*|stimulat\w*|induc\w*|promot\w*|enhanc\w*|elevat\w*|higher|rais\w*|boost\w*"),
    ("associates_with", r"associat\w*|correlat\w*|linked|link\w*|co-?occur\w*|enriched"),
    ("interacts", r"interact\w*|bind\w*|bound"),
    ("regulates", r"regulat\w*|modulat\w*|alter\w*|affect\w*|influenc\w*|control\w*"),
]
_TRIGGER_RES = [(t, re.compile(r"\b(?:" + p + r")\b", re.I)) for t, p in TRIGGERS]

NOMINAL_PRODUCES = re.compile(r"^[\s-]*(producer|producing|-producing)\b", re.I)
NOMINAL_CONSUMES = re.compile(r"^[\s-]*(degrader|degrading|utilizer|-degrading)\b", re.I)
SOURCE = re.compile(r"^\s*(from|of)\s*$", re.I)
PASSIVE_AGENT = re.compile(r"^\s*by\s*$", re.I)
PRODUCT_LINK = re.compile(r"^\s*(to|into|to form|yielding|forming)\s*$", re.I)
SUBSTRATE_LINK = re.compile(r"^\s*(from|through|via)\s*$", re.I)
COORD_LINK = re.compile(r"^\s*(,|and|or|,\s*and|,\s*or|as well as)\s*$", re.I)
MICROBE_COORD = re.compile(r"^\s*(and|or|nor|as well as)\s*$", re.I)
NEGATION = re.compile(r"\b(not|no|never|neither|nor|without|unable|fail(?:ed|s)?\s+to|lack(?:ed|s|ing)?|absent"
                      r"|independent\s+of|n't)\b", re.I)
PRE_NEGATION = re.compile(r"\b(neither|nor)\s*$", re.I)
HEDGE = re.compile(r"\b(may|might|could|suggest\w*|possibl\w*|potential\w*|putative|likely)\b", re.I)
CLAUSE_SPLIT = re.compile(r";|,?\s+\b(?:whereas|while|but|although|however)\b", re.I)

BASE_CONF = {"produces": 0.8, "consumes": 0.8, "converts": 0.8, "inhibits": 0.75, "activates": 0.75,
             "associates_with": 0.7, "interacts": 0.7, "regulates": 0.65}
MAX_GAP = 150


@dataclass
class _Trigger:
    type: str
    start: int
    end: int


def _triggers(text: str, offset: int = 0) -> list[_Trigger]:
    found: list[_Trigger] = []
    for rel_type, rx in _TRIGGER_RES:
        for m in rx.finditer(text):
            s, e = m.start() + offset, m.end() + offset
            if any(t.start < e and s < t.end for t in found):
                continue
            found.append(_Trigger(rel_type, s, e))
    return sorted(found, key=lambda t: t.start)


def _clauses(sentence: str) -> list[tuple[int, int]]:
    bounds, start = [], 0
    for m in CLAUSE_SPLIT.finditer(sentence):
        bounds.append((start, m.start()))
        start = m.end()
    bounds.append((start, len(sentence)))
    return bounds


def _clause_of(pos: int, clauses: list[tuple[int, int]]) -> int:
    for k, (s, e) in enumerate(clauses):
        if s <= pos < e or (k == len(clauses) - 1 and pos >= s):
            return k
    return len(clauses) - 1


def _mask(sentence: str, entities: list[Entity], lo: int, hi: int) -> str:
    """Text of sentence[lo:hi] with entity mentions blanked, so names don't trigger rules."""
    chars = list(sentence[lo:hi])
    for e in entities:
        for i in range(max(e.start, lo), min(e.end, hi)):
            chars[i - lo] = " "
    return "".join(chars)


def _sentence_relations(sentence: str, pmid: str | None) -> list[Relationship]:
    ents = extract_entities(sentence, strict=True)
    microbes = sorted([e for e in ents if e.label == "MICROBE"], key=lambda e: e.start)
    mets = sorted([e for e in ents if e.label == "METABOLITE"
                   and not any(m.start < e.end and e.start < m.end for m in microbes)], key=lambda e: e.start)
    if not microbes or not mets:
        return []

    clauses = _clauses(sentence)
    hedged = bool(HEDGE.search(sentence))
    out: list[Relationship] = []

    for mic in microbes:
        mc = _clause_of(mic.start, clauses)
        assigned: dict[int, str] = {}  # metabolite start -> type for this microbe (coordination)
        for met in mets:
            xc = _clause_of(met.start, clauses)
            carry = False
            if xc != mc:
                # Carry a sentence-initial subject into a later clause without its own microbe.
                clause_has_microbe = any(_clause_of(m.start, clauses) == xc for m in microbes)
                subject_initial = mic.start - clauses[mc][0] <= 1 and mic is microbes[0]
                if not (xc > mc and subject_initial and not clause_has_microbe):
                    continue
                carry = True

            rel = _classify_pair(sentence, mic, met, microbes, mets, clauses, xc if carry else mc,
                                 carry, assigned)
            if rel is None:
                continue
            rel_type, conf, negated = rel
            assigned[met.start] = rel_type
            if hedged:
                conf -= 0.15
            out.append(Relationship(
                microbe=mic.text, microbe_type=mic.entity_type, metabolite=met.text,
                metabolite_class=met.entity_type, relationship_type=rel_type,
                confidence=round(min(max(conf, 0.1), 0.95), 3), evidence_sentence=sentence.strip(),
                article_pmid=pmid, extraction_method="rules_v2", negated=negated,
            ))
    return out


def _classify_pair(sentence, mic, met, microbes, mets, clauses, clause_idx, carry, assigned):
    """Return (type, confidence, negated) for one microbe-metabolite pair, or None."""
    cs, ce = clauses[clause_idx]
    ents = microbes + mets

    if carry:
        lo, hi = cs, met.start
    elif mic.start < met.start:
        lo, hi = mic.end, met.start
    else:
        lo, hi = met.end, mic.start
    if hi - lo > MAX_GAP:
        return None
    between = _mask(sentence, ents, lo, hi)

    # Subject check: a non-coordinated microbe between the pair owns the verb.
    for other in microbes:
        if other is mic or not (lo <= other.start < hi):
            continue
        if mic.start < met.start:
            link = sentence[mic.end:other.start]
            if not MICROBE_COORD.match(link):
                return None
    # Negation scoped to this pair.
    negated = bool(NEGATION.search(between)) or bool(PRE_NEGATION.search(sentence[max(cs, mic.start - 12):mic.start]))

    microbe_first = carry or mic.start < met.start
    if microbe_first:
        trig = _triggers(between, lo)
        if not trig:
            tail = sentence[met.end:met.end + 25]
            if NOMINAL_PRODUCES.match(tail):
                return "produces", 0.7, negated
            if NOMINAL_CONSUMES.match(tail):
                return "consumes", 0.7, negated
            return None
        t = trig[-1]  # nearest to the metabolite
        rel_type, conf = t.type, BASE_CONF[t.type]
        prior = [m for m in mets if t.end <= m.start < met.start]
        if prior:
            y = prior[-1]
            link = sentence[y.end:met.start]
            if PRODUCT_LINK.match(link):
                rel_type = "produces"
            elif SUBSTRATE_LINK.match(link):
                rel_type = "consumes"
            elif COORD_LINK.match(link):
                rel_type = assigned.get(y.start, rel_type)
                conf -= 0.05
            else:
                return None  # e.g. "produced H2S in cysteine-rich media": cysteine is a distractor
        if hi - lo > 60:
            conf -= 0.1
        return rel_type, conf, negated

    # Metabolite first: passive voice, source phrase, or the metabolite acts on the microbe.
    if SOURCE.match(between):
        return "produces", 0.75, negated
    trig = _triggers(between, lo)
    if not trig and PASSIVE_AGENT.match(between):
        trig = _triggers(_mask(sentence, ents, cs, met.start), cs)
        if not trig:
            return None
        t = trig[-1]
        link = sentence[t.end:met.start]
        prior = [m for m in mets if t.end <= m.start < met.start]
        if PRODUCT_LINK.match(link) or (prior and PRODUCT_LINK.match(sentence[prior[-1].end:met.start])):
            return "produces", 0.7, negated
        return t.type, BASE_CONF[t.type] - 0.1, negated
    if not trig:
        return None
    t = trig[0]  # nearest to the metabolite (which comes first)
    conf = BASE_CONF[t.type] - (0.1 if hi - lo > 60 else 0.0)
    return t.type, conf, negated


def extract_relationships_v2(text: str, pmid: str | None = None, max_sentences: int = 500) -> list[Relationship]:
    """All pair relations, including negated ones (flagged with negated=True)."""
    if not text:
        return []
    rels: list[Relationship] = []
    for sentence in _split_sentences(text)[:max_sentences]:
        rels.extend(_sentence_relations(sentence, pmid))
    best: dict[tuple, Relationship] = {}
    for r in rels:
        key = (r.microbe.lower(), r.metabolite.lower(), r.negated)
        if key not in best or r.confidence > best[key].confidence:
            best[key] = r
    return list(best.values())
