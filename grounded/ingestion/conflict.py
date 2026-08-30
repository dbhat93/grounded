"""Source-of-truth conflict detection.

The real failure mode of a sales knowledge base: the same fact lives in a Sheet,
a wiki, a SharePoint doc, and Slack, and they disagree. When two sources make
different claims about the same topic, we do NOT silently pick one. We flag it
for curation and hold both out of the served KB until a human resolves it.
"""
from collections import defaultdict


class Conflict:
    def __init__(self, topic_key, facts):
        self.topic_key = topic_key
        self.facts = facts

    def statuses(self):
        return sorted({f.status for f in self.facts})


def detect(candidates):
    groups = defaultdict(list)
    for c in candidates:
        groups[c.topic_key].append(c)
    conflicts = []
    for key, facts in groups.items():
        if len(facts) < 2:
            continue
        statuses = {f.status.strip().lower() for f in facts}
        if len(statuses) > 1:                      # disagree on live-vs-roadmap
            conflicts.append(Conflict(key, facts))
    return conflicts


def conflicted_keys(conflicts):
    return {c.topic_key for c in conflicts}
