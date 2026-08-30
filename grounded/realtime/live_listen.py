"""Local private earpiece: capture a live call's audio on THIS Mac, transcribe
it locally with Whisper, and whisper grounded cite-or-refuse cards to the rep.
Nothing leaves the machine (no cloud STT, no bot in the meeting).

The trick that makes speaker attribution free: Meet / Zoom / Teams never route
your own microphone back to your own speakers, so whatever comes out of the call
output is only the *other* side. Tap that output and every utterance we hear is
a buyer turn. Your own voice is never captured.

One-time setup (macOS) to tap the call output:
    brew install blackhole-2ch
    # Audio MIDI Setup -> create a Multi-Output Device with your real output
    # + BlackHole 2ch, and select it as the call app's / system output so you
    # still hear the call while BlackHole gets a copy.
Then:
    python -m grounded meeting-bot --list-devices     # find BlackHole's index
    python -m grounded meeting-bot --live              # auto-picks BlackHole
    python -m grounded meeting-bot --live --device 3 --model small.en

No BlackHole yet? `--mic` taps the default input instead: put the call on
speaker and it will hear both sides (lower quality, and it will also hear you).

Design note: the audio-I/O (LiveListener) and the segmentation logic (Segmenter)
are separated so the segmentation is unit-testable with synthetic frames and no
hardware. See tests/test_realtime.py.
"""
import queue
import re
import sys

import numpy as np

SR = 16000          # whisper wants 16 kHz mono
BLOCK = 1600        # 0.1 s capture blocks
DEFAULT_THRESHOLD = 0.01   # RMS above this counts as speech (BlackHole is clean digital)
DEFAULT_SILENCE_S = 0.7    # trailing silence that ends an utterance
DEFAULT_MIN_S = 0.4        # ignore blips shorter than this
DEFAULT_MAX_S = 12.0       # force-flush a monologue this long

# Whisper hallucinates these on near-silence; drop them so they never trigger.
_HALLUCINATIONS = {
    "you", "thank you.", "thanks for watching!", "thank you for watching.",
    ".", "bye.", "okay.", "so", "the", "mm-hmm.", "yeah.", "uh.",
}
_TRAILING = re.compile(r"[\s/\\|_>]+$")   # base.en tacks these onto trailing tones
_WS = re.compile(r"\s+")
_ALNUM = re.compile(r"[^a-z0-9]+")


def clean_transcript(text):
    """Strip the artifacts base.en appends on trailing tones and normalize space."""
    return _WS.sub(" ", _TRAILING.sub("", (text or "").strip())).strip()


def is_noise(text):
    """True if this transcript is empty, sub-verbal, or a known hallucination."""
    low = text.lower()
    if len(_ALNUM.sub("", low)) < 2:
        return True
    return low in _HALLUCINATIONS


class Segmenter:
    """Energy-based utterance segmentation, decoupled from audio I/O so it can be
    unit-tested with synthetic frames. Feed it fixed-size blocks with push();
    it returns a completed utterance (a float32 array) or None. Speech starts
    when RMS crosses an adaptive threshold and an utterance ends after a beat of
    trailing silence (or a hard max length)."""

    def __init__(self, base_threshold=DEFAULT_THRESHOLD, silence_s=DEFAULT_SILENCE_S,
                 min_s=DEFAULT_MIN_S, max_s=DEFAULT_MAX_S, block=BLOCK, sr=SR):
        self.base = base_threshold
        self.sil_blocks = max(1, round(silence_s * sr / block))
        self.min_len = min_s * sr
        self.max_len = max_s * sr
        self.floor = base_threshold / 4.0     # adaptive ambient-noise estimate
        self.buf = []
        self.voiced = False
        self.voiced_len = 0                   # speech samples only (excludes trailing silence)
        self.sil = 0

    @staticmethod
    def _rms(block):
        return float(np.sqrt(np.mean(np.square(block, dtype=np.float64))) + 1e-9)

    def _flush(self):
        audio = np.concatenate(self.buf) if self.buf else None
        voiced_len = self.voiced_len
        self.buf, self.voiced, self.voiced_len, self.sil = [], False, 0, 0
        # gate on actual speech content, not the trailing-silence padding
        return audio if (audio is not None and voiced_len >= self.min_len) else None

    def push(self, block):
        rms = self._rms(block)
        thr = max(self.base, self.floor * 4.0)
        if rms <= thr:
            self.floor = 0.95 * self.floor + 0.05 * rms   # track the quiet ambient level
        if rms > thr:
            self.voiced, self.sil = True, 0
            self.buf.append(block)
            self.voiced_len += len(block)
        elif self.voiced:
            self.buf.append(block)        # keep trailing silence so words are not clipped
            self.sil += 1
        total = sum(len(b) for b in self.buf)
        if self.voiced and (self.sil >= self.sil_blocks or total >= self.max_len):
            return self._flush()
        return None


def _sd():
    try:
        import sounddevice as sd
        return sd
    except Exception as e:  # pragma: no cover - env-dependent
        sys.exit("live mode needs sounddevice: pip install sounddevice\n(%s)" % e)


def list_devices():
    sd = _sd()
    print("Input-capable audio devices (use the index with --device):\n")
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) < 1:
            continue
        star = "  <- BlackHole (use this to tap the call)" if "blackhole" in d["name"].lower() else ""
        print("  [%2d] %-40s  in=%d%s" % (i, d["name"][:40], d["max_input_channels"], star))
    print("\nNo BlackHole? Install it (brew install blackhole-2ch) so the Mac can "
          "tap the call output, or use --mic for a quick speaker test.")
    return 0


def _auto_device(sd):
    """Prefer a BlackHole input so we tap the call output, not the room mic."""
    for i, d in enumerate(sd.query_devices()):
        if d.get("max_input_channels", 0) >= 1 and "blackhole" in d["name"].lower():
            return i, d["name"]
    return None, None


class LiveListener:
    """Opens the input stream and feeds blocks through a Segmenter, yielding
    completed utterances. Thin I/O shell; the logic lives in Segmenter."""

    def __init__(self, device=None, **seg_kwargs):
        self.device = device
        self.seg = Segmenter(**seg_kwargs)

    def utterances(self):
        sd = _sd()
        q = queue.Queue()

        def cb(indata, frames, time_info, status):
            q.put(indata[:, 0].copy())

        with sd.InputStream(samplerate=SR, channels=1, dtype="float32",
                            blocksize=BLOCK, device=self.device, callback=cb):
            while True:
                utt = self.seg.push(q.get())
                if utt is not None:
                    yield utt


class Transcriber:
    def __init__(self, model_name="base.en"):
        import whisper
        sys.stderr.write("loading whisper (%s), one moment...\n" % model_name)
        self.model = whisper.load_model(model_name)

    def text(self, audio):
        r = self.model.transcribe(audio.astype(np.float32), language="en",
                                  fp16=False, condition_on_previous_text=False,
                                  no_speech_threshold=0.5)
        return clean_transcript(r.get("text") or "")


def run_live(device_arg=None, model_name="base.en", mode="lexical",
             use_mic=False, threshold=DEFAULT_THRESHOLD):
    """Wire the local listener into the meeting bot. Every heard utterance is a
    buyer turn (see module docstring), so it goes straight to bot.hear."""
    from .meeting_bot import MeetingBot, whisper_card
    sd = _sd()

    device, name = None, "default input"
    if device_arg is not None:
        device = int(device_arg)
        name = sd.query_devices(device)["name"]
    elif not use_mic:
        device, name = _auto_device(sd)
        if device is None:
            sys.exit("No BlackHole input found. Install it (brew install blackhole-2ch) "
                     "and route the call's output through it, or run with --mic to tap "
                     "the default input. See --list-devices.")
        name = "%s (call tap)" % name

    bot = MeetingBot(mode)
    tx = Transcriber(model_name)
    listener = LiveListener(device=device, base_threshold=threshold)

    print("\nGrounded live earpiece. Listening on: %s" % name)
    print("Everything I hear here is the buyer side. I whisper a grounded card on "
          "a vetted answer, flag a refusal on a clear question, and stay silent "
          "otherwise. Ctrl-C to stop.\n")
    try:
        for audio in listener.utterances():
            text = tx.text(audio)
            if not text or is_noise(text):
                continue
            r = bot.hear("Buyer", text)
            if r:
                whisper_card(r)
    except KeyboardInterrupt:
        print("\nstopped.")
    return 0
