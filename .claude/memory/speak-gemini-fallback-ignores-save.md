---
name: speak-gemini-fallback-ignores-save
description: "speak_gemini's kokoro fallback ignores --save/--no-play and plays aloud; cloud TTS needs fresh gcloud ADC"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2be61392-0223-4be0-b571-1d7471c67169
---

`speak_gemini --save x.mp3 --no-play` only honors those flags on the CLOUD path. When
cloud TTS fails (typically expired Google application-default credentials — error 503
"Reauthentication is needed"), it falls back to `speak_kokoro`, which is play-only: the
narration plays aloud through the speakers immediately and NO file is saved (exit 2).
`speak_kokoro` has no save option at all.

Observed 2026-07-20 generating the extender-db status-briefing audio: Henry heard the
briefing live from what was meant to be a silent save-to-file run.

**How to apply:** before a save-to-file TTS run, either confirm cloud auth works or expect
the fallback to play aloud. Reauth is interactive and Henry-only: suggest he run
`! gcloud auth application-default login`. If a saved artifact is required and cloud is
down, there is no local path — keep the narration script as the durable artifact instead.
