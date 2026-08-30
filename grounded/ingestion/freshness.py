"""Freshness: is a candidate fact too old to trust, given its claim class?

A fresh-looking wrong answer is worse than no answer, so every fact carries a
last_verified and a ttl_class, and this pass marks anything past its TTL stale.
"""
from datetime import date, datetime

from .model import TTL_DAYS


def days_since(iso):
    try:
        d = datetime.strptime(iso, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    return (date.today() - d).days


def assess(candidate):
    ttl = TTL_DAYS.get(candidate.ttl_class, TTL_DAYS["default"])
    d = days_since(candidate.last_verified)
    candidate.stale_days = d
    candidate.stale = (d is not None and d > ttl)
    return candidate
