"""Unit tests for the live earpiece internals that need no audio hardware:
utterance segmentation, transcript cleaning, and the bot's speak/stay-silent
decision. Run with:  python -m tests.test_realtime   (or pytest).

The live audio capture (sounddevice InputStream) and Whisper are deliberately
NOT tested here: they are thin I/O shells over the logic below, and the full
speech->grounding path is exercised separately by the say(1) pipeline check.
"""
import numpy as np

from grounded.realtime.live_listen import (
    Segmenter, clean_transcript, is_noise, SR, BLOCK,
)
from grounded.realtime.meeting_bot import MeetingBot


def _blocks(pattern, speech_level=0.05):
    """Turn a string of 's' (speech) / '.' (silence) into BLOCK-sized frames."""
    out = []
    rng = np.random.default_rng(0)
    for ch in pattern:
        if ch == "s":
            out.append((rng.standard_normal(BLOCK) * speech_level).astype(np.float32))
        else:
            out.append(np.zeros(BLOCK, dtype=np.float32))
    return out


def _feed(seg, blocks):
    return [utt for b in blocks if (utt := seg.push(b)) is not None]


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("  ok:", msg)


def test_segments_one_utterance_after_trailing_silence():
    # ~1.2 s of speech, then enough silence (0.7 s = 7 blocks) to close it.
    seg = Segmenter()
    utts = _feed(seg, _blocks("s" * 12 + "." * 8))
    check(len(utts) == 1, "one utterance emitted after trailing silence")
    check(len(utts[0]) >= seg.min_len, "utterance meets min length")


def test_short_blip_is_dropped():
    seg = Segmenter()   # min_s 0.4 => needs >4 speech blocks
    utts = _feed(seg, _blocks("ss" + "." * 8))
    check(utts == [], "sub-min blip produces no utterance")


def test_two_utterances_split_by_pause():
    seg = Segmenter()
    utts = _feed(seg, _blocks("s" * 10 + "." * 8 + "s" * 10 + "." * 8))
    check(len(utts) == 2, "two utterances split by a pause")


def test_max_length_force_flush():
    # Continuous speech longer than max_s must flush without waiting for silence.
    seg = Segmenter(max_s=1.0)   # 1 s => 10 blocks
    utts = _feed(seg, _blocks("s" * 25))
    check(len(utts) >= 2, "long monologue force-flushed into chunks")


def test_clean_transcript_strips_whisper_artifacts():
    check(clean_transcript("do you integrate with Salesforce? //") ==
          "do you integrate with Salesforce?", "strips trailing // artifact")
    check(clean_transcript("  hello   world  ") == "hello world", "collapses whitespace")
    check(clean_transcript("") == "", "empty stays empty")


def test_is_noise_filters_hallucinations():
    check(is_noise("Thank you.") is True, "known hallucination filtered")
    check(is_noise(".") is True, "punctuation-only filtered")
    check(is_noise("a") is True, "sub-verbal single char filtered")
    check(is_noise("do you support SSO?") is False, "real question kept")


def test_bot_grounds_refuses_and_stays_silent():
    bot = MeetingBot("lexical")
    # a vetted question -> a card
    r = bot.hear("Buyer", "do you integrate with Salesforce?")
    check(r is not None and not r["refused"], "grounds a vetted buyer question")
    # an unvettable question (not in the KB) -> an explicit refusal card
    r = bot.hear("Buyer", "do you support integration with SAP Ariba?")
    check(r is not None and r["refused"], "refuses an unvettable question")
    # the rep's own turn -> silence (never coaches off the seller)
    r = bot.hear("rep", "yeah we integrate with Salesforce natively")
    check(r is None, "stays silent on the rep's own turn")
    # small talk with no entity and no question -> silence
    r = bot.hear("Buyer", "great, thanks for hopping on today")
    check(r is None, "stays silent on entity-free small talk")


def test_bot_cooldown_suppresses_repeat():
    bot = MeetingBot("lexical")
    first = bot.hear("Buyer", "do you integrate with Salesforce?")
    second = bot.hear("Buyer", "wait, remind me about Salesforce integration?")
    check(first is not None and not first["refused"], "first Salesforce card fires")
    check(second is None, "same topic within cooldown is suppressed")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    print("running %d realtime tests\n" % len(tests))
    for t in tests:
        print(t.__name__)
        t()
    print("\nall %d realtime tests passed." % len(tests))


if __name__ == "__main__":
    main()
