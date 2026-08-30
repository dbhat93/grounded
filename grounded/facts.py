"""The Fact model and the knowledge loader.

A Fact (still called Item for now) is one vetted unit of knowledge. Provenance
(source), freshness (last_verified), and live-vs-roadmap status are fields, not
afterthoughts. The loader reads the fictional Kestrel KB from JSONL today; the
same Item shape is what a database-backed store returns later.
"""
import json
import os

from .text import tokenize

PKG_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(PKG_DIR)
# Prefer a KB bundled inside the installed package (grounded/kb); fall back to
# the repo-root kb/ in development. This lets a pip-installed copy be
# self-contained (needed for the PyPI package the MCP registry points at).
_PKG_KB = os.path.join(PKG_DIR, "kb")
KB_DIR = _PKG_KB if os.path.isdir(_PKG_KB) else os.path.join(REPO_ROOT, "kb")
EVAL_PATH = os.path.join(REPO_ROOT, "evals", "eval_set.jsonl")

# Hand-authored, vetted facts.
BASE_KB_FILES = [
    os.path.join(KB_DIR, "qa.jsonl"),
    os.path.join(KB_DIR, "capabilities.jsonl"),
    os.path.join(KB_DIR, "competitors.jsonl"),
]
# Facts promoted from ingestion (coverage-gated, conflict/stale excluded). Written
# by `python3 -m grounded promote`. Kept separate so promotion is auditable and
# reversible.
PROMOTED_FILE = os.path.join(KB_DIR, "promoted.jsonl")

# The served KB = hand-authored + promoted.
KB_FILES = BASE_KB_FILES + [PROMOTED_FILE]

STATUS_LABELS = {
    "ga": "GA",
    "beta": "BETA",
    "roadmap": "ROADMAP",
    "not supported": "NOT SUPPORTED",
    "battle card": "BATTLE CARD",
}

# One-line caution appended for anything not live-and-generally-available.
STATUS_CAUTION = {
    "BETA": "Beta, not GA. Do not present as generally available; confirm access.",
    "ROADMAP": "Roadmap, not shipped. Do not present as available today.",
    "NOT SUPPORTED": "Not supported. Say so plainly; do not imply a workaround exists.",
}


class Item:
    """One vetted fact, normalized across source files."""

    def __init__(self, id, kind, topic, answer, status, last_verified, source,
                 topic_key=None):
        self.id = id
        self.kind = kind                  # qa | capability | competitor
        self.topic_key = topic_key or id  # twins across sources share a key
        self.topic = topic                # the question / entity the fact is about
        self.answer = answer              # the vetted claim, returned verbatim
        self.status = status
        self.status_label = STATUS_LABELS.get(status.strip().lower(), status.upper())
        self.last_verified = last_verified
        self.source = source
        # Search text: weight the topic over the answer body so a match is driven
        # by what the fact is *about*, not incidental answer words.
        self.tokens = tokenize(topic) * 3 + tokenize(answer)
        self.tokenset = set(tokenize(topic)) | set(tokenize(answer))
        # Topic-only tokens: used to break near-ties so a negative fact that
        # mentions the real product in its body ("...not Fiserv DNA...") does not
        # out-match the real fact on a DNA question.
        self.topic_tokenset = set(tokenize(topic))


def load_kb(paths=None):
    items = []
    for path in (paths or KB_FILES):
        if not os.path.exists(path):
            continue                          # promoted.jsonl may not exist yet
        base = os.path.basename(path)
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if "question" in row:        # qa.jsonl
                    items.append(Item(
                        id=row["id"], kind="qa", topic=row["question"],
                        answer=row["answer"], status=row["status"],
                        last_verified=row.get("last_verified", ""), source=base,
                        topic_key=row.get("topic_key"),
                    ))
                elif "competitor" in row:    # competitors.jsonl (battle cards)
                    items.append(Item(
                        id=row["id"], kind="competitor", topic=row["competitor"],
                        answer=row["answer"], status=row["status"],
                        last_verified=row.get("last_verified", ""), source=base,
                        topic_key=row.get("topic_key"),
                    ))
                elif "claim" in row and "provenance" in row:   # promoted.jsonl
                    p = row["provenance"]
                    src = "%s/%s [%s]" % (p.get("source_system", ""),
                                          p.get("doc_title", ""), p.get("locator", ""))
                    items.append(Item(
                        id=row["id"], kind="promoted", topic=row["topic"],
                        answer=row["claim"], status=row["status"],
                        last_verified=row.get("last_verified", ""), source=src,
                        topic_key=row.get("topic_key"),
                    ))
                else:                        # capabilities.jsonl
                    items.append(Item(
                        id=row["id"], kind="capability",
                        topic=row["capability"], answer=row["detail"],
                        status=row["status"],
                        last_verified=row.get("last_verified", ""), source=base,
                        topic_key=row.get("topic_key"),
                    ))
    return items
