"""Turn extracted units into candidate facts (documents) or mined questions
(transcripts). This is where provenance and a freshness class attach, and where
the trust boundary is enforced: transcripts never yield facts.
"""
import re

from ..text import tokenize
from .model import CandidateFact, MinedQuestion, SourceRef


def _slug(topic):
    toks = tokenize(topic)
    return "-".join(toks[:4]) if toks else "unknown"


def _infer_status(text):
    t = text.lower()
    if "not supported" in t or "does not" in t or "no automated" in t:
        return "Not supported"
    if "roadmap" in t or "targeted" in t or "not available today" in t:
        return "Roadmap"
    if "beta" in t:
        return "Beta"
    return "GA"   # a posture/spec statement with no hedge reads as live


def _ttl_class(status, topic, claim):
    s, blob = status.lower(), (topic + " " + claim).lower()
    if s == "battle card":
        return "competitor"
    if s == "roadmap":
        return "roadmap"
    if any(w in blob for w in ("pricing", "cost", "trial", "discount")):
        return "pricing"
    if any(w in blob for w in ("soc", "pci", "encrypt", "residency", "security",
                               "sso", "retention", "hipaa")):
        return "security"
    return "capability"


def _ref(raw, locator):
    return SourceRef(raw.source_system, raw.doc_id, raw.title, locator, raw.fetched_at)


def _fact(raw, unit, topic, claim, status, last_verified):
    status = status or "GA"
    return CandidateFact(
        topic_key=_slug(topic), topic=topic.strip(), claim=claim.strip(),
        status=status, last_verified=last_verified or raw.source_last_modified,
        ttl_class=_ttl_class(status, topic, claim), provenance=_ref(raw, unit.locator))


def _col(fields, *names):
    for n in names:
        for k, v in fields.items():
            if k.lower() == n.lower():
                return v
    return ""


def factify_doc(raw, units):
    """Documents -> candidate facts."""
    out = []
    if raw.fmt == "xlsx":
        for u in units:
            f = u.fields
            cap = _col(f, "Capability")
            q = _col(f, "Question")
            if cap:
                out.append(_fact(raw, u, cap, _col(f, "Detail") or cap,
                                 _col(f, "Status"), _col(f, "Last Verified")))
            elif q:
                out.append(_fact(raw, u, q, _col(f, "Answer"),
                                 _col(f, "Status"), _col(f, "Last Verified")))
    elif raw.fmt == "docx":
        for u in units:
            heading = u.fields.get("heading", "")
            body = u.fields.get("body", "")
            lv = u.fields.get("doc_last_reviewed", "")
            if heading and body:
                out.append(_fact(raw, u, heading, body, _infer_status(body), lv))
    elif raw.fmt == "pdf":
        for u in units:
            text = u.fields.get("text", "")
            topic = _pdf_topic(text) or raw.title
            status = "Battle card" if "battle card" in text.lower() else _infer_status(text)
            m = re.search(r"last verified:\s*(\d{4}-\d{2}-\d{2})", text, re.I)
            out.append(_fact(raw, u, topic, text, status, m.group(1) if m else ""))
    return out


def _pdf_topic(text):
    # "Competitive Battle Card: SentinelIQ" -> "SentinelIQ"
    first = text.strip().splitlines()[0] if text.strip() else ""
    if ":" in first:
        return first.split(":", 1)[1].strip()
    return first.strip()


_QWORDS = ("do ", "does ", "can ", "are ", "is ", "what ", "how ", "which ", "will ", "would ")


def mine_questions(raw, units):
    """Transcripts -> mined buyer questions. UNVETTED; never facts."""
    out = []
    for u in units:
        speaker = u.fields.get("speaker", "").lower()
        said = u.fields.get("said", "")
        if speaker in ("rep", "ae", "se", "seller"):
            continue
        low = said.lower()
        if "?" in said or low.startswith(_QWORDS):
            for q in re.split(r"(?<=\?)\s+", said):
                q = q.strip()
                if "?" in q or q.lower().startswith(_QWORDS):
                    out.append(MinedQuestion(question=q, provenance=_ref(raw, u.locator)))
    return out
