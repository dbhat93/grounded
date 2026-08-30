"""The structured / deterministic layer, and question routing.

Some questions have exactly one correct value: is a capability live or roadmap,
is a certification held, is an integration supported. Those are deterministic
and must be answered by an exact lookup against a structured fact, never by a
similarity search that could fuzzy-match to the wrong answer. Everything else is
open-ended and stays on the probabilistic (retrieval) path.

The structured fact here is the triple hiding in every KB entry:
(entity, status, GA|Beta|Roadmap|Not-supported). The router owns availability
questions that name a single entity; it defers otherwise, so the guarantee is
never weakened, only sharpened.
"""
from dataclasses import dataclass

from .text import tokenize, build_strong_tokens
from .grounding import Result, disqualifies

# Words that signal an availability / status question (matched as substrings on
# the raw query, since some, like "integration", are stopwords in tokenize).
AVAIL_KEYWORDS = (
    "support", "integrat", "available", "availabilit", "live", "roadmap",
    "offer", "certif", "authoriz", "complian", "in production", "shipping",
    "generally available", " ga ", " ga?", "beta",
)


def availability_intent(query):
    low = " " + query.lower().strip() + " "
    return any(kw in low for kw in AVAIL_KEYWORDS)


def value_intent(query):
    low = query.lower()
    return "what" in low or "how " in low


@dataclass
class ValueFact:
    """A single-value fact, addressed by trigger tokens and citing a KB entry.
    The entry's vetted answer carries the value, so routing here is about which
    fact to return exactly, not about extracting a snippet."""
    label: str
    source_key: str        # KB topic_key that holds the vetted value
    triggers: frozenset     # distinctive tokens that identify this value question


# The single-value facts the router owns. Each cites an existing KB fact so
# provenance and freshness flow through unchanged. Triggers are distinctive so a
# value question maps to exactly one of these or to none.
VALUE_FACTS = [
    ValueFact("Uptime SLA",           "sla-uptime",         frozenset({"sla", "uptime"})),
    ValueFact("Scoring latency",      "realtime-scoring",   frozenset({"latency"})),
    ValueFact("Data retention period", "retention",         frozenset({"retention", "retain"})),
    ValueFact("Implementation time",  "implementation-time", frozenset({"implementation"})),
    ValueFact("Support hours",        "support-hours",      frozenset({"hour"})),
]


class StructuredFact:
    """One (entity, status) triple, with the entity's proper-noun tokens for
    matching and the source item for the answer text and citation."""

    def __init__(self, item, strong_tokens):
        self.item = item
        self.entity = item.topic
        self.entity_key = item.topic_key
        self.status_label = item.status_label
        self.entity_strong = set(tokenize(item.topic)) & strong_tokens


class StructuredLayer:
    def __init__(self, items):
        self.strong_tokens = build_strong_tokens(
            [it.topic for it in items] + [it.answer for it in items])
        # one triple per entity: collapse twins, prefer the qa talk-track
        best = {}
        for it in items:
            k = it.topic_key
            if k not in best or (best[k].kind != "qa" and it.kind == "qa"):
                best[k] = it
        self.by_key = best
        self.facts = [StructuredFact(it, self.strong_tokens) for it in best.values()]

    def lookup(self, query):
        """Return a deterministic Result, or None to defer to the probabilistic
        path. Tries the (entity, status) triples first, then the value triples;
        both defer rather than guess when the match is not unique."""
        return self._status_lookup(query) or self._value_lookup(query)

    def _status_lookup(self, query):
        """Availability question naming exactly one known entity -> its status."""
        if not availability_intent(query):
            return None
        qtokens = tokenize(query)
        qstrong = set(qtokens) & self.strong_tokens
        if not qstrong:
            return None
        scored = [(f, len(qstrong & f.entity_strong)) for f in self.facts]
        scored = [(f, s) for f, s in scored if s > 0]
        if not scored:
            return None
        scored.sort(key=lambda x: x[1], reverse=True)
        if len(scored) > 1 and scored[0][1] == scored[1][1]:
            return None                       # ambiguous entity: defer, do not guess
        fact = scored[0][0]
        if disqualifies(qtokens, fact.item):  # e.g. "SOC 1" against the SOC 2 triple
            return None
        return Result("answer", items=[fact.item], scores=[1.0],
                      qtokens=qtokens, deterministic=True)

    def _value_lookup(self, query):
        """Value question ('what is your uptime SLA') -> the one vetted fact that
        holds that value, by distinctive trigger tokens."""
        if not value_intent(query):
            return None
        qtokens = tokenize(query)
        qset = set(qtokens)
        scored = [(vf, len(vf.triggers & qset)) for vf in VALUE_FACTS]
        scored = [(vf, s) for vf, s in scored if s > 0]
        if not scored:
            return None
        scored.sort(key=lambda x: x[1], reverse=True)
        if len(scored) > 1 and scored[0][1] == scored[1][1]:
            return None
        item = self.by_key.get(scored[0][0].source_key)
        if item is None or disqualifies(qtokens, item):
            return None
        return Result("answer", items=[item], scores=[1.0],
                      qtokens=qtokens, deterministic=True)


class RoutedIndex:
    """Deterministic-first router: try the structured lookup, else fall through
    to a probabilistic base retriever (lexical or hybrid). The grounding
    contract is unchanged; this only adds an exact path in front of it."""

    def __init__(self, items, base):
        self.items = items
        self.structured = StructuredLayer(items)
        self.base = base
        self.strong_tokens = self.structured.strong_tokens

    def answer(self, query):
        det = self.structured.lookup(query)
        if det is not None:
            return det
        return self.base.answer(query)
