"""Tokenization and entity (strong-token) detection.

Pure, dependency-free text utilities shared by every retriever and by the
grounding contract. No knowledge of facts or scoring lives here.
"""
import re

# Question boilerplate carries no topic signal. Dropping it keeps a match driven
# by the distinctive nouns (Fiserv, SOC 2, encryption) so an off-domain question
# like "do you integrate with SAP ERP" scores ~0 rather than latching onto a
# shared "do you integrate with".
STOPWORDS = set("""
a an the this that these those and or but if then else of to in on for with without
do does did you your yours we us our ours they them their it its is are was were be been
being have has had can could should would will shall may might must about into over under
integrate integrates integrated integration integrations
offer offers offered provide provides provided provided give gives given handle handles
what which who whom whose where when why how much many any some all there here as at by from
i me my mine so than too very just also
""".split())

_word_re = re.compile(r"[a-z0-9]+")
_rawword_re = re.compile(r"[A-Za-z0-9][A-Za-z0-9\-]*")


def _norm(tok):
    """Crude singularize so 'webhooks' matches 'webhook'."""
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok


def tokenize(text):
    """Lowercase, split to word tokens, drop stopwords, crudely singularize.
    Keeps single digits ('SOC 2', '1.2') but drops single letters."""
    tokens = []
    for tok in _word_re.findall(text.lower()):
        if tok in STOPWORDS or (len(tok) < 2 and not tok.isdigit()):
            continue
        tok = _norm(tok)
        if tok in STOPWORDS:
            continue
        tokens.append(tok)
    return tokens


def build_strong_tokens(texts):
    """Proper nouns and acronyms (Salesforce, SAML, SOC, Fiserv, Finastra): a
    match on one of these alone is trustworthy because the buyer named it, and
    a mention of one is the trigger for live watch mode.

    Detect them by case across the whole corpus: a token is 'strong' if it
    always appears with an uppercase letter and never as a purely-lowercase
    word. That separates real brands/acronyms (always capitalized) from common
    words that merely happen to start a sentence ('Retention', 'Check', 'Data'),
    which also appear lowercase elsewhere and so are not strong."""
    seen_lower, seen_caps = set(), set()
    for text in texts:
        for w in _rawword_re.findall(text):
            has_upper = any(c.isupper() for c in w)
            for piece in _word_re.findall(w.lower()):
                if piece in STOPWORDS or (len(piece) < 2 and not piece.isdigit()):
                    continue
                piece = _norm(piece)
                (seen_caps if has_upper else seen_lower).add(piece)
    strong = {t for t in seen_caps if t not in seen_lower}
    strong -= {"yes", "no"}   # sentence-initial affirmations, not brands
    return strong
