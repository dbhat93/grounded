"""The knowledge / ingestion layer.

Pulls documents and transcripts from mocked enterprise sources, extracts them
(real xlsx/pdf/docx/transcript parsing over fixtures), and turns documents into
candidate facts with provenance and a freshness class, while mining transcripts
only for questions. Detects source-of-truth conflicts and holds them for
curation. See ARCHITECTURE section 7.
"""
from .pipeline import run, IngestionReport
from .model import (SUPPORTED_FORMATS, SUPPORTED_SOURCES, TRANSCRIPT_PROVIDERS,
                    TRUSTED_FOR_FACTS)

__all__ = ["run", "IngestionReport", "SUPPORTED_FORMATS", "SUPPORTED_SOURCES",
           "TRANSCRIPT_PROVIDERS", "TRUSTED_FOR_FACTS"]
