"""Source connectors.

Local and transcript files are read for real. The cloud connectors (Google
Drive, SharePoint, Office 365) are MOCKED: they declare the formats they can
supply and return fixture documents tagged with their source system, but they do
no real auth and make no API calls. Wiring real enterprise auth (OAuth, Graph
API, service accounts) is a deliberate later step; the pipeline above them does
not change when that happens, because everything speaks RawDoc.
"""
import os

from ..facts import REPO_ROOT
from .model import RawDoc

FIXTURES = os.path.join(REPO_ROOT, "fixtures")
TODAY = "2026-08-07"

_EXT_FMT = {".xlsx": "xlsx", ".pdf": "pdf", ".docx": "docx", ".txt": "transcript"}


def _fmt_of(path):
    return _EXT_FMT.get(os.path.splitext(path)[1].lower(), "unknown")


class Connector:
    source_system = None

    def fetch(self):
        """Return a list[RawDoc]."""
        raise NotImplementedError


class LocalFileConnector(Connector):
    source_system = "local"

    def __init__(self, specs):
        # specs: list of (doc_id, title, filename, source_last_modified)
        self.specs = specs

    def fetch(self):
        docs = []
        for doc_id, title, fname, mod in self.specs:
            path = os.path.join(FIXTURES, fname)
            docs.append(RawDoc(self.source_system, doc_id, title, _fmt_of(path),
                               path, TODAY, mod))
        return docs


class _MockCloudConnector(Connector):
    """Shared base for the mocked cloud connectors. Real auth/API is a stub."""

    def __init__(self, specs):
        self.specs = specs   # (doc_id, title, filename, source_last_modified)

    def authenticate(self):
        # MOCK. Real: OAuth service account (Google), MS Graph app token
        # (SharePoint/365). Returns a placeholder so callers see the shape.
        return {"mock_token": self.source_system}

    def fetch(self):
        self.authenticate()
        docs = []
        for doc_id, title, fname, mod in self.specs:
            path = os.path.join(FIXTURES, fname)
            docs.append(RawDoc(self.source_system, doc_id, title, _fmt_of(path),
                               path, TODAY, mod))
        return docs


class GoogleDriveConnector(_MockCloudConnector):
    source_system = "google_drive"


class SharePointConnector(_MockCloudConnector):
    source_system = "sharepoint"


class Office365Connector(_MockCloudConnector):
    source_system = "office365"


class TranscriptConnector(Connector):
    """MOCK call/meeting-intelligence connector. Real: Gong/Otter/Granola/Zoom/
    Sybill/Wispr/Minutes export APIs. Transcript content is UNTRUSTED and is
    never promoted to a fact; the pipeline mines questions from it only."""
    source_system = "transcript"

    def __init__(self, specs):
        # specs: list of (provider, doc_id, title, filename, source_last_modified)
        self.specs = specs

    def fetch(self):
        docs = []
        for provider, doc_id, title, fname, mod in self.specs:
            path = os.path.join(FIXTURES, fname)
            docs.append(RawDoc(self.source_system, doc_id, title, _fmt_of(path),
                               path, TODAY, mod, provider=provider))
        return docs


def default_connectors():
    """The mock enterprise setup: a spread across every supported source."""
    return [
        GoogleDriveConnector([
            ("gsheet-cap-01", "Capability Matrix (Sheet)", "capability_matrix.xlsx", "2026-07-18"),
            ("gsheet-sig-01", "Security Questionnaire (Sheet)", "security_questionnaire.xlsx", "2026-05-30"),
        ]),
        SharePointConnector([
            ("sp-sec-01", "Security Posture", "security_posture.docx", "2026-07-25"),
        ]),
        Office365Connector([
            ("o365-price-01", "Pricing Guide", "pricing_guide.docx", "2026-05-30"),
        ]),
        LocalFileConnector([
            ("local-bc-01", "SentinelIQ Battle Card", "battle_card_sentineliq.pdf", "2026-01-15"),
        ]),
        TranscriptConnector([
            ("gong", "call-acme-01", "Acme Bank discovery", "transcript_gong_acme_bank.txt", "2026-08-05"),
        ]),
    ]
