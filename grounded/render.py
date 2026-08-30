"""Rendering of grounded Results for the CLI and the live watch surface.

Freshness (staleness) is surfaced here today; a dedicated freshness module with
per-claim TTL classes is a Phase 2 concern (see ARCHITECTURE).
"""
from datetime import date, datetime

from .facts import STATUS_CAUTION

STALE_DAYS = 90   # older than this, flag "re-confirm before quoting"


def days_since(iso_date):
    try:
        d = datetime.strptime(iso_date, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None
    return (date.today() - d).days


def stale_flag(item):
    d = days_since(item.last_verified)
    if d is not None and d > STALE_DAYS:
        return "  [!] STALE: verified %d days ago, re-confirm before quoting" % d
    return ""


def render(result):
    if result.kind == "refuse":
        lines = [
            "NOT IN THE KNOWLEDGE BASE",
            'Say: "I don\'t have that vetted, I\'ll follow up in writing." Do not guess.',
        ]
        if result.note:
            lines.append("Reason: " + result.note)
        if result.items:
            lines.append("(closest entry %s at %.2f; too weak or too few matched "
                         "terms to answer safely)"
                         % (result.items[0].id, result.scores[0]))
        return "\n".join(lines)

    it = result.items[0]
    sc = result.scores[0]
    lines = ["[%s]  %s" % (it.status_label, it.topic), "", it.answer]
    caution = STATUS_CAUTION.get(it.status_label)
    if caution:
        lines += ["", ">> " + caution]
    if getattr(result, "deterministic", False):
        conf = "exact (deterministic lookup)"
    else:
        conf = "confidence %.2f" % sc
    lines += ["", "Source: %s (%s), verified %s   %s%s"
              % (it.id, it.source, it.last_verified, conf, stale_flag(it))]
    return "\n".join(lines)


def render_live(line, result):
    """Compact, glance-able surface for live watch mode: one labeled card."""
    it = result.items[0]
    out = ['  >> heard: "%s"' % line.strip()]
    caution = STATUS_CAUTION.get(it.status_label)
    out.append("     [%s] %s" % (it.status_label, it.topic))
    out.append("     %s" % it.answer)
    if caution:
        out.append("     !! " + caution)
    out.append("     src %s, verified %s%s" % (it.id, it.last_verified, stale_flag(it)))
    return "\n".join(out)
