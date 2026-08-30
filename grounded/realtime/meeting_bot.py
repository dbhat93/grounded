"""Minimum-testable meeting bot: drive a live (or simulated) meeting transcript
through the grounded engine and whisper cite-or-refuse cards to the rep.

The only new piece over the `watch` mode is the transcript SOURCE. Three are
provided, all reusing the grounding / entity-trigger / refusal engine unchanged
so the bot inherits "never wrong out loud" for free:

  1. local file / stdin  - simulated transcript, testable now with no account.
  2. live local earpiece - capture the real call's audio ON THIS MAC, transcribe
     with local Whisper, whisper cards to the rep. Nothing leaves the machine.
     See live_listen.py; run `python -m grounded meeting-bot --live`.
  3. Recall.ai handler   - a cloud bot joins the call and POSTs transcript events
     to your webhook (egress). See recall_transcript_event() below.

Test now (simulated meeting):
    python -m grounded meeting-bot evals/sample_call.txt
    tail -f transcript.txt | python -m grounded meeting-bot -

Real Google Meet / Zoom (local, private, no cloud):
    python -m grounded meeting-bot --list-devices
    python -m grounded meeting-bot --live
"""
import re
import sys

from .. import cli
from ..facts import STATUS_CAUTION
from ..text import tokenize

_LINE = re.compile(r"^\s*(?:\[([^\]]+)\]\s*)?([A-Za-z][\w .'-]*?):\s*(.*)$")
_REP_SPEAKERS = {"rep", "ae", "se", "seller", "sales", "us", "me"}
_QWORDS = ("do ", "does ", "can ", "are ", "is ", "what ", "how ", "which ",
           "will ", "would ", "could ", "who ")


def _is_buyer(speaker):
    return speaker.strip().lower() not in _REP_SPEAKERS


def _is_question(text):
    low = text.lower()
    return "?" in text or low.startswith(_QWORDS)


class MeetingBot:
    """Consumes buyer turns, decides when to speak, and returns a whisper card
    (a grounded answer or a refusal) or None to stay silent."""

    def __init__(self, mode="lexical"):
        self.index = cli.build_index(mode, routed=True)
        self.triggers = self.index.strong_tokens
        self.fired = {}
        self.i = 0

    def hear(self, speaker, text):
        self.i += 1
        if not _is_buyer(speaker) or not text.strip():
            return None
        named_entity = bool(set(tokenize(text)) & self.triggers)
        if not named_entity and not _is_question(text):
            return None
        res = self.index.answer(text)
        if res.kind != "answer":
            # only whisper a refusal when the buyer clearly asked something
            return {"refused": True, "line": text} if _is_question(text) else None
        it = res.items[0]
        if it.topic_key in self.fired and self.i - self.fired[it.topic_key] < 6:
            return None
        self.fired[it.topic_key] = self.i
        return {"refused": False, "item": it, "line": text}


def whisper_card(res):
    line = res["line"].strip()
    print('  heard: "%s"' % line[:76])
    if res["refused"]:
        print('    >> WHISPER: not vetted. Say "I will follow up in writing." Do not guess.\n')
        return
    it = res["item"]
    print("    >> [%s] %s" % (it.status_label, it.answer[:96]))
    cap = STATUS_CAUTION.get(it.status_label)
    if cap:
        print("       !! " + cap)
    print("       src %s, verified %s\n" % (it.id, it.last_verified))


def _turns(lines):
    for raw in lines:
        m = _LINE.match(raw.rstrip("\n"))
        if m:
            yield m.group(2).strip(), m.group(3).strip()


def run_meeting_bot(lines, mode="lexical"):
    bot = MeetingBot(mode)
    print("Grounded meeting bot. Whispers a grounded card on buyer turns; silent "
          "otherwise. (Simulated transcript; run --live for a real call.)\n")
    for speaker, text in _turns(lines):
        r = bot.hear(speaker, text)
        if r:
            whisper_card(r)
    return 0


def run_meeting_bot_cli(args):
    args = list(args)

    if "--list-devices" in args:
        from .live_listen import list_devices
        return list_devices()

    if "--live" in args:
        from .live_listen import run_live
        use_mic = "--mic" in args
        device = _opt(args, "--device")
        model = _opt(args, "--model") or "base.en"
        thr = _opt(args, "--threshold")
        return run_live(device_arg=device, model_name=model, use_mic=use_mic,
                        threshold=float(thr) if thr else 0.01)

    # file / stdin (simulated transcript), unchanged
    positional = [a for a in args if not a.startswith("-")]
    if positional and positional[0] != "-":
        with open(positional[0], encoding="utf-8") as fh:
            return run_meeting_bot(fh.readlines())
    return run_meeting_bot(sys.stdin)


def _opt(args, flag):
    """Value after `flag` in argv, or None."""
    if flag in args:
        i = args.index(flag)
        if i + 1 < len(args):
            return args[i + 1]
    return None


def recall_transcript_event(event, bot):
    """Handle one Recall.ai real-time transcript event for a live call.

    Setup: create a bot with Recall's API (POST /api/v1/bot with the meeting
    URL and real_time_transcription pointing at your webhook), set RECALL_API_KEY,
    and expose a small HTTPS endpoint (Flask/FastAPI) that constructs one
    MeetingBot and calls this per event. Recall handles joining Zoom / Meet /
    Teams; you only handle the text. Note this streams the call audio to your
    cloud (the egress bet in ARCHITECTURE); local ASR is the no-egress swap.
    """
    data = event.get("data", {})
    text = " ".join(w.get("text", "") for w in data.get("words", [])).strip()
    speaker = (data.get("participant") or {}).get("name") or "Buyer"
    r = bot.hear(speaker, text)
    if r:
        whisper_card(r)
