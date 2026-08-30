"""Grounded: a trust-first answer layer for high-trust sales.

Never wrong out loud. Every output is either a vetted, cited, labeled claim or
an explicit refusal. See ARCHITECTURE.md for the invariant and the design.
"""
from .facts import Item, load_kb
from .grounding import Result, finalize, collapse_twins, disqualifies
from .text import tokenize, build_strong_tokens
from .retrieval import LexicalIndex, DenseIndex, HybridIndex

__all__ = [
    "Item", "load_kb",
    "Result", "finalize", "collapse_twins", "disqualifies",
    "tokenize", "build_strong_tokens",
    "LexicalIndex", "DenseIndex", "HybridIndex",
]
