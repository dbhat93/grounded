"""The grounding contract: the gate that makes the guarantee true.

Deterministic. No model in the loop. Input is a query plus ranked candidates
from any retriever; output is one vetted fact (with label + citation) or an
explicit refusal. Retrievers and models are swappable behind this module; the
promise ("never wrong out loud") lives here and only here.
"""

# Two candidates within this score gap, pointing at different facts, are a
# near-tie and get the lexical-anchor tiebreak below.
AMBIGUITY_MARGIN = 0.05

# Lexical token gate: a match on one incidental shared word ("policy", "fraud")
# is not grounds to answer. Require at least this many shared content tokens,
# with two exceptions handled in the gate.
MIN_SHARED_TOKENS = 2

# One-word-question exception: the single shared token must be distinctive
# (rare in the corpus), not generic. df<=2 in the current KB clears ~2.5.
DISTINCTIVE_IDF = 2.5


class Result:
    def __init__(self, kind, items=None, scores=None, qtokens=None, note=None,
                 deterministic=False):
        self.kind = kind                  # "answer" | "refuse"
        self.items = items or []
        self.scores = scores or []
        self.qtokens = qtokens or []
        self.note = note                  # why we refused, when relevant
        self.deterministic = deterministic  # answered by exact structured lookup


def collapse_twins(scored):
    """Merge candidates sharing a topic_key so a fact stored in two places is one
    result, not a false near-tie. Keep the highest score for the key, and prefer
    the qa fact (it carries the talk-track answer) as the representative."""
    best = {}
    order = []
    for it, sc in scored:
        k = it.topic_key
        if k not in best:
            best[k] = [it, sc]
            order.append(k)
        else:
            cur_item, cur_sc = best[k]
            new_sc = max(cur_sc, sc)
            if cur_item.kind != "qa" and it.kind == "qa":
                best[k] = [it, new_sc]
            else:
                best[k][1] = new_sc
    collapsed = [(best[k][0], best[k][1]) for k in order]
    collapsed.sort(key=lambda x: x[1], reverse=True)
    return collapsed


def disqualifies(qtokens, item):
    """Number/version guard: a question pinning a number the matched fact does
    not carry must not answer from it ('SOC 1' vs a SOC 2 fact, 'ISO 27001',
    'TLS 1.3'). Brand variants ('Fiserv Premier') are handled by curated
    not-supported facts, not a heuristic. Returns a reason to refuse, or None."""
    for t in qtokens:
        if t.isdigit() and t not in item.tokenset:
            return 'question pins "%s", which this entry does not cover' % t
    return None


def token_gate(index, scored, qset, qtokens):
    """Lexical-only precision gate. Keep facts sharing enough content tokens with
    the query. A single shared token answers only when it is a proper-noun /
    acronym the buyer named, or is the whole one-word question."""
    def eligible(it):
        shared = qset & it.tokenset
        if len(shared) >= MIN_SHARED_TOKENS:
            return True
        if len(shared) == 1:
            tok = next(iter(shared))
            if tok in index.strong_tokens:
                return True
            if len(qtokens) == 1 and index.idf.get(tok, 0.0) >= DISTINCTIVE_IDF:
                return True
        return False
    return [(it, sc) for it, sc in scored if eligible(it)]


def finalize(index, scored, qtokens):
    """Run the contract over one retriever's ranked candidates. Collapse twins,
    (lexical only) apply the token gate, refuse below the retriever's threshold,
    run the number guard, break near-ties by lexical anchor, else answer."""
    scored = collapse_twins(scored)
    qset = set(qtokens)
    if getattr(index, "token_gate", False):
        scored = token_gate(index, scored, qset, qtokens)
    if not scored or scored[0][1] < index.threshold:
        closest = scored[:1]
        return Result("refuse", items=[i for i, _ in closest],
                      scores=[s for _, s in closest], qtokens=qtokens)
    top_item, top_score = scored[0]
    reason = disqualifies(qtokens, top_item)
    if reason:
        return Result("refuse", items=[top_item], scores=[top_score],
                      qtokens=qtokens, note=reason)
    if len(scored) > 1:
        second_item, second_score = scored[1]
        if (top_score - second_score) < AMBIGUITY_MARGIN and \
                second_item.topic_key != top_item.topic_key:
            # Near-tie. Break by which fact the question actually names (topic
            # tokens). No lexical signal either way is a coin-flip: refuse.
            t1 = len(qset & top_item.topic_tokenset)
            t2 = len(qset & second_item.topic_tokenset)
            if t2 > t1:
                top_item, top_score = second_item, second_score
            elif t1 == t2:
                return Result("refuse", items=[top_item], scores=[top_score],
                              qtokens=qtokens,
                              note="two entries match about equally; not confident which")
    return Result("answer", items=[top_item], scores=[top_score], qtokens=qtokens)
