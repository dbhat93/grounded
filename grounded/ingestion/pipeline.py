"""The ingestion pipeline: connectors -> raw docs -> extract -> factify ->
freshness -> conflict detection. Produces an IngestionReport.

Documents yield candidate facts (vettable). Transcripts yield mined questions
(unvetted). Nothing here writes to the served KB; acceptance is a curation
decision gated on conflicts and freshness.
"""
from .connectors import default_connectors
from .extract import extract
from .factify import factify_doc, mine_questions
from .freshness import assess
from .conflict import detect, conflicted_keys
from .model import TRUSTED_FOR_FACTS


class IngestionReport:
    def __init__(self):
        self.docs = []          # RawDoc
        self.facts = []         # CandidateFact (from documents)
        self.questions = []     # MinedQuestion (from transcripts)
        self.conflicts = []     # Conflict
        self.stale = []         # CandidateFact flagged stale

    def accepted(self):
        """Facts safe to serve: fresh and not in a conflict."""
        blocked = conflicted_keys(self.conflicts)
        return [f for f in self.facts
                if not f.stale and f.topic_key not in blocked]

    def held(self):
        """Facts held back for curation (stale or conflicting)."""
        blocked = conflicted_keys(self.conflicts)
        return [f for f in self.facts if f.stale or f.topic_key in blocked]


def run(connectors=None):
    connectors = connectors or default_connectors()
    report = IngestionReport()
    for conn in connectors:
        for raw in conn.fetch():
            report.docs.append(raw)
            units = extract(raw)
            if raw.fmt == "transcript":
                report.questions.extend(mine_questions(raw, units))
            elif raw.source_system in TRUSTED_FOR_FACTS:
                for f in factify_doc(raw, units):
                    assess(f)
                    report.facts.append(f)
    report.stale = [f for f in report.facts if f.stale]
    report.conflicts = detect(report.facts)
    return report
