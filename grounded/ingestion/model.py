"""Ingestion data model: raw documents, extracted units, candidate facts, and
the provenance and freshness that ride with every fact.

Provenance and freshness are not metadata bolted on later; they are the point of
this layer. A fact with no source and no verified date cannot be served.
"""
from dataclasses import dataclass, field
from typing import Optional

# Supported file formats. XLSX / PDF / DOCX are extracted for real; the cloud
# formats arrive as one of these (a Google Sheet is xlsx, a Google/Word doc is
# docx) through a source connector. "transcript" is plain-text call/meeting
# transcript content.
SUPPORTED_FORMATS = {
    "xlsx": "Excel workbook (real extraction)",
    "pdf": "PDF document (real extraction)",
    "docx": "Word document (real extraction)",
    "transcript": "Call / meeting transcript (real extraction, question mining)",
}

# Supported source systems. Local is real; the cloud and transcript connectors
# are MOCKED (they declare support and return fixtures; real auth and API calls
# are a later wiring step, deliberately out of scope here).
SUPPORTED_SOURCES = {
    "local": "Local filesystem (real)",
    "google_drive": "Google Drive / Workspace enterprise (MOCK)",
    "sharepoint": "SharePoint (MOCK)",
    "office365": "Microsoft 365 / Office Online (MOCK)",
    "transcript": "Call / meeting intelligence (MOCK)",
}

# Transcript providers the transcript connector can pull from.
TRANSCRIPT_PROVIDERS = {
    "granola", "wispr", "minutes", "gong", "zoom", "otter", "sybill",
}

# THE TRUST BOUNDARY. Documents are vettable knowledge and can become served
# facts. Transcripts are UNTRUSTED conversation: a rep can say something wrong on
# a call. Transcript content is never auto-promoted to a served fact. Instead it
# is mined for the questions buyers asked (for coverage and gap analysis), and a
# human must promote anything before it becomes a fact.
TRUSTED_FOR_FACTS = {"local", "google_drive", "sharepoint", "office365"}

# Freshness policy: how many days a claim of each class stays trustworthy before
# it must be re-verified. Different claims decay at different rates.
TTL_DAYS = {
    "security": 180,     # posture, certs, encryption
    "capability": 120,   # GA feature claims
    "pricing": 90,       # pricing and packaging
    "roadmap": 60,       # roadmap / beta timing moves fast
    "competitor": 45,    # competitive claims go stale fastest
    "default": 120,
}


@dataclass
class RawDoc:
    """A document as pulled from a source, before any extraction."""
    source_system: str        # one of SUPPORTED_SOURCES
    doc_id: str               # stable id within that source
    title: str
    fmt: str                  # one of SUPPORTED_FORMATS
    path: str                 # local path to the bytes (fixture, for the mock)
    fetched_at: str           # ISO date the connector pulled it
    source_last_modified: str = ""   # from the source system, if known
    provider: str = ""        # for transcripts: gong / otter / granola / ...


@dataclass
class MinedQuestion:
    """A buyer question observed on a transcript. UNVETTED: it never becomes a
    fact on its own. It feeds coverage and gap analysis, and a human may promote
    it into the eval set or curate an answer."""
    question: str
    provenance: "SourceRef"
    covered: Optional[bool] = None       # does the served KB answer it?
    answer_id: Optional[str] = None      # which fact, if covered


@dataclass
class ExtractedUnit:
    """A structural piece of a document (a spreadsheet row, a doc section, a
    page block) with a precise locator for citation."""
    locator: str              # "Capabilities!row5", "section: EU data residency"
    text: str
    fields: dict = field(default_factory=dict)


@dataclass
class SourceRef:
    """Where a fact came from, precisely enough to cite and to re-verify."""
    source_system: str
    doc_id: str
    doc_title: str
    locator: str
    fetched_at: str


@dataclass
class CandidateFact:
    """A fact proposed by ingestion, not yet accepted into the served KB."""
    topic_key: str
    topic: str
    claim: str
    status: str
    last_verified: str
    ttl_class: str
    provenance: SourceRef
    stale: Optional[bool] = None       # filled in by the freshness pass
    stale_days: Optional[int] = None
