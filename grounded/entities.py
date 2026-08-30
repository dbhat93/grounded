"""Entity resolution.

The precise half of dedup and conflict keying. A "hard entity" is a token that
names a specific product or standard unambiguously: an ALLCAPS acronym (SOC,
PCI, DNA, T24) or a CamelCase brand (ServiceNow, FedRAMP, SharePoint). These are
safe to key on, unlike a common word that merely happens to be capitalized as a
heading (Encryption, Retention), which is not a hard entity.

Used to fix the promotion dedup false-positive: semantic coverage may say a
candidate is "covered", but if the candidate names a hard entity the covering
fact does not share, it is a *different* entity and must not be deduped away
(ServiceNow is not Salesforce, even though both do "case sync").
"""
import re

from .text import STOPWORDS, _word_re, _norm

_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]*")
_ACRONYM = re.compile(r"^[A-Z0-9]{2,6}$")


def _is_acronym(core):
    return bool(_ACRONYM.match(core)) and any(c.isalpha() for c in core)


def _is_camel(core):
    # an uppercase letter after the first position, not fully uppercase
    return any(c.isupper() for c in core[1:]) and not core.isupper()


def hard_entities(text):
    """Return the set of distinctive brand/acronym tokens in a string."""
    ents = set()
    for w in _TOKEN.findall(text):
        core = w.strip("-")
        if not core:
            continue
        if _is_acronym(core) or _is_camel(core):
            for p in _word_re.findall(core.lower()):
                if p not in STOPWORDS and len(p) >= 2:
                    ents.add(_norm(p))
    return ents


def same_entity(candidate_text, covering_text):
    """True if the candidate does not introduce a hard entity the covering text
    lacks. False means the candidate names a different specific thing, so a
    semantic 'covered' verdict should be overridden to net-new."""
    cand = hard_entities(candidate_text)
    if not cand:
        return True                      # no hard entity: defer to semantics
    cover = hard_entities(covering_text)
    return cand.issubset(cover)
