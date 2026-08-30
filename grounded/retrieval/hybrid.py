"""Hybrid retrieval: an ensemble of two independently-grounded pipelines.

Rather than fuse raw scores (whose scales differ and whose absolute value the
refusal decision depends on), we run the lexical and dense pipelines each
through the full grounding contract, then combine their *verdicts*:

  - either pipeline confidently answers  -> take that answer (union recall:
    dense rescues a lexical synonym miss; lexical rescues a dense proper-noun
    miss)
  - both answer, same fact               -> answer
  - both answer, different facts         -> break by which fact the question
    names (lexical anchor); a true tie refuses
  - both refuse                          -> refuse

Because each pipeline is tuned to zero-wrong at its own threshold, the union
stays zero-wrong on the eval while recovering what either alone would miss.
"""
from ..text import tokenize
from ..grounding import Result
from .lexical import LexicalIndex
from .dense import DenseIndex


class HybridIndex:
    token_gate = False

    def __init__(self, items, model=None):
        self.items = items
        self.lexical = LexicalIndex(items)
        self.dense = DenseIndex(items, model=model)
        self.strong_tokens = self.lexical.strong_tokens   # for live watch triggers

    def answer(self, query):
        qtokens = tokenize(query)
        lr = self.lexical.answer(query)
        dr = self.dense.answer(query)
        la = lr.kind == "answer"
        da = dr.kind == "answer"

        if la and da:
            if lr.items[0].topic_key == dr.items[0].topic_key:
                return lr                      # agree; prefer the qa talk-track
            qset = set(qtokens)
            lt = len(qset & lr.items[0].topic_tokenset)
            dt = len(qset & dr.items[0].topic_tokenset)
            if lt > dt:
                return lr
            if dt > lt:
                return dr
            return Result("refuse", items=[lr.items[0]], scores=lr.scores,
                          qtokens=qtokens,
                          note="lexical and semantic retrieval disagree; not confident")
        if la:
            return lr
        if da:
            return dr
        return lr   # both refuse; either refusal is fine
