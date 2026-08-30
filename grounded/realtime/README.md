# Grounded live earpiece

Grounded, listening to a real sales call and whispering a vetted card to the rep
the moment the buyer asks something. Same cite-or-refuse engine as the CLI, so it
inherits "never wrong out loud" for free. The only new thing is where the words
come from.

Two forms:

- **`meeting-bot <file>`** replays a transcript (a saved call, or a `tail -f`
  stream) through the engine. No account, testable right now.
- **`meeting-bot --live`** captures a real Meet / Zoom / Teams call on this Mac,
  transcribes it locally with Whisper, and whispers cards to you. Nothing leaves
  the machine.

## Why local, not a cloud bot

The obvious build is a bot that joins the meeting (Recall.ai and friends), sends
the audio to the cloud, and posts a transcript back. That works, and the seam for
it is still here (`recall_transcript_event` in `meeting_bot.py`). But it has two
costs: a visible bot in the room, and every word of a regulated sales call
leaving your infrastructure.

The local earpiece avoids both. It taps the call audio on your own machine, runs
a local Whisper model, and shows cards only to you. No bot appears in the call, no
audio egresses, and it works in any meeting app because it listens to the audio,
not the app.

## Speaker attribution is free

A live copilot has to know who is talking. Coaching the rep on the rep's own
words is worse than useless. Here the OS solves it: Meet, Zoom, and Teams never
route your own microphone back to your own speakers, so the call's output audio is
only the other side. Tap that output and every utterance is a buyer turn. Your
voice is never captured, so there is nothing to filter.

(The `--mic` fallback taps your default input instead, for a quick test with the
call on speaker. That one does hear both sides and is lower quality. It exists so
you can try the flow before installing anything.)

## One-time setup (macOS)

To tap the call's output you need a virtual audio device. BlackHole is the free
standard.

```bash
brew install blackhole-2ch
```

Then, so you still hear the call while BlackHole gets a copy, make a Multi-Output
Device:

1. Open **Audio MIDI Setup** (in `/Applications/Utilities`).
2. Click **+** at the bottom left, **Create Multi-Output Device**.
3. Check both your real output (MacBook speakers or your headphones) and
   **BlackHole 2ch**.
4. Set that Multi-Output Device as the output for your call app (or as the system
   output). You keep hearing the call; BlackHole receives the same audio.

Confirm BlackHole shows up as an input:

```bash
python -m grounded meeting-bot --list-devices
```

You should see a `BlackHole 2ch` row flagged as the call tap.

## Run it

```bash
python -m grounded meeting-bot --live                 # auto-picks BlackHole
python -m grounded meeting-bot --live --device 3      # or pin a device index
python -m grounded meeting-bot --live --model small.en # more accuracy, more latency
python -m grounded meeting-bot --live --mic           # no BlackHole: tap default input
```

While a call is running it prints one line when it hears the buyer, and a card
when it has something vetted to say:

```
  heard: "and what about Corelation Keystone, that's our credit union core?"
    >> [NOT SUPPORTED] Kestrel integrates with Jack Henry Symitar (Episys) and
       Fiserv DNA, not the Corelation Keystone core.
       !! Not supported. Say so plainly; do not imply a workaround exists.
       src CAP-23, verified 2026-06-14
```

On a clear buyer question it cannot vet, it whispers a refusal instead of a guess:

```
  heard: "do you support integration with SAP Ariba?"
    >> WHISPER: not vetted. Say "I will follow up in writing." Do not guess.
```

Otherwise it stays silent. It fires on a named entity or a clear question, holds a
per-topic cooldown so the same card does not repeat, and never speaks on the rep's
own turn.

## How it stays never-wrong through a bad transcript

Whisper mishears things. The design assumes it. Two examples from the test run:

- "Corelation Keystone" came through as "correlation keystone" (lowercase, wrong
  homophone). The curated negative fact still caught it and said NOT SUPPORTED
  rather than answering with the wrong core.
- Trailing tones make `base.en` append junk like `//`. `clean_transcript` strips
  it before the text ever reaches the engine.

The deeper reason it holds: the answer is a vetted fact returned verbatim, and the
same shared-token gate, number guard, and refusal threshold from the CLI run on
the transcribed text. A noisy transcript can cause a miss (the engine stays quiet
when it should have spoken). It does not cause a confident wrong answer. That is
the trade the whole product is built around.

## Files

```
live_listen.py    audio capture (LiveListener), energy-based segmentation
                  (Segmenter, unit-tested), local Whisper (Transcriber),
                  transcript cleaning, and the --live wiring
meeting-bot.py    the MeetingBot decision (speak / refuse / stay silent), the
                  transcript-file replay, and the Recall.ai cloud seam
```

Tests for the segmentation, transcript cleaning, and the speak/silent decision
are in `tests/test_realtime.py` and need no audio hardware.

## Limits

- macOS setup instructions only. Linux/Windows can tap system audio too (PulseAudio
  monitor, VB-Cable), the listener does not care which device it reads.
- The entity/question trigger is high-precision. A capability asked in plain words
  with no named product may not fire. Widening the trigger trades recall for noise.
- `base.en` is the default for speed. `--model small.en` is more accurate and
  still local, at more latency per utterance.
