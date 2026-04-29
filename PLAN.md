# Brazilian-Portuguese Voice Dub for Star Fox 64 — Plan

## Table of Contents
- [Goal](#goal)
- [Current state](#current-state)
- [Architecture](#architecture)
- [Stage 1 — Map every voice line](#stage-1--map-every-voice-line)
- [Stage 2 — Translate the scripts](#stage-2--translate-the-scripts)
- [Stage 3 — Recording](#stage-3--recording)
- [Stage 4 — Manifest population & QA](#stage-4--manifest-population--qa)
- [Stage 5 — Distribution](#stage-5--distribution)
- [Engineering follow-ups](#engineering-follow-ups)
- [Reference](#reference)

---

## Goal

Ship a complete Brazilian-Portuguese voice dub for Star Fox 64 (Starship port) covering every voice line in the game (~780 entries in `gMsgLookup`) with matching pt-BR text, distributable as a small drop-in package alongside the existing community translation mod.

---

## Current state

**Proof-of-concept complete and validated** — see [`PROOF_OF_CONCEPT.md`](./PROOF_OF_CONCEPT.md) for the full architectural breakdown.

The Corneria mission briefing now plays:
- Radio click intro (untouched)
- pt-BR Pepper: *"Que bom que apareceram, Star Fox! Vocês são nossa única esperança."*
- Radio click between speakers
- pt-BR Fox: *"Vou sentar o dedo! Dessa vez o Andross não vai se dar bem!"*
- Radio click outro
- Matching pt-BR text in the radio bubble

End-to-end: native audio rate, full sentence duration, no English bleed-through, all SFX intact, no crashes. Drop-in install alongside the existing `SF64 - TraducaoPT-BR.o2r` text mod.

The infrastructure scales to all 779 remaining voice lines without further engine work. Adding a line is 3 data edits (no rebuild).

---

## Architecture

Two parallel channels, both data-driven:

### Audio
`Audio_PlayVoice(msgId)` is intercepted in `src/audio/audio_general.c`. The intercept reads a routing table from `voice_manifest.txt` (loaded at runtime on first call). For msgIds in the manifest:
- Skip the seq dispatcher (or partially run it for SFX preservation, controlled by `letSeqRunForMsgIds`).
- Kick off the mapped pt-BR WAV via `PlaySoundA(SND_FILENAME | SND_ASYNC)`.

For msgIds not in the manifest, fall through to the original seq-player path — all other voices in the game (and the cutscene's BGM/SFX) keep working normally.

### Text
`tools/dub/pack_text_o2r.py` reads `ptbr_audio/lines.csv` directly, encodes each `script_pt` cell into SF64's glyph table (accents stripped — the font has no diacritics; literal `\n` becomes a newline glyph), and produces `mods/SF64-DubPT-BR.o2r`. The community translation mod is archived in `ptbr_audio/_archive/` and not loaded by default; if reintroduced into `mods/` it sorts alphabetically *before* `SF64-DubPT-BR.o2r`, so the dub's `gMsg_ID_<n>` overrides still win.

### Why not engine-side sample replacement (rejected)
We prototyped the obvious approach: pack pt-BR PCM into an `.o2r` overriding the original sample resources. Three blockers, all detailed in `PROOF_OF_CONCEPT.md`:

1. **Multi-note dispatch**: the seq fires multiple "phoneme replacement" notes per voice line; even with dedup, restarts fragment our WAV into `Que…Que bom…Que…`.
2. **Note-duration mismatch**: the seq schedules ~250 ms phoneme notes; our 5+ s recordings get clipped.
3. **`sample_3310` hard crash**: overriding `fontId=1 inst=7`'s sample crashes Starship — root cause unidentified after several debugging passes.

The seq player was designed for short ADPCM phonemes; making it play full-sentence PCM correctly requires either rewriting the voice-sequence bytecode (out of scope) or fighting the engine on every note dispatch. The bypass intercepts before that complexity ever runs.

---

## Stage 1 — Map every voice line

**Goal:** know which msgIds map to each character's lines, in order, for every gameplay context.

We need to capture every msgId fired during a full playthrough — both the radio-chatter ones (most have on-screen text) and the cutscene-only ones (msgIds 1–60ish, no on-screen text). The community text translation has been removed from `mods/` so the in-game view is now original English, which makes Stage 1 capture cleaner: every visible line is the original script.

### Master inventory: `ptbr_audio/lines.csv`
Single source of truth for the entire dub. Semicolon-delimited (`;`), one row per voice line, header on row 1. Columns:

| Column | Description |
|---|---|
| `msgId` | The numeric msgId whose **on-screen text** we want to override. For lines whose audio fires on a different msgId than the displayable text (e.g., Pepper's intro: audio cue is msgId=3, displayable text is msgId=1200), use the displayable msgId here. Empty for not-yet-mapped lines. |
| `mission` | Mission/level name (Corneria, Meteo, Sector X, …) or `-` for non-mission contexts (title screen, map screen, etc.). Metadata for filtering/grouping; not consumed by any tool. |
| `character` | Pepper, Fox, Falco, Slippy, Peppy, ROB 64, Wolf, Leon, Pigma, Andrew, Bill, Katt, Andross, etc. |
| `action` | Short descriptor of the in-game moment (e.g. "intro", "boss approach", "ally rescued"), or `-` if not applicable. Metadata. |
| `script_en` | Original English text (translator reference; not consumed). |
| `script_pt` | Pt-BR text — used for **both** the spoken recording target AND the displayed radio-bubble text (they always match in this dub). Use `\n` for line breaks in the bubble; the packer expands them. Accents are stripped at pack time (SF64 font has no diacritic glyphs). |
| `wav_file` | Path **relative to `ptbr_audio/`**, organized in character subfolders (e.g. `pepper/01_que_bom.wav`, `fox/01_vou_sentar_o_dedo.wav`). May repeat across rows when one recording covers multiple msgIds. |
| `is_complete` | `yes` / `no` — workflow tracking. Recording done, manifest entries added, in-game verified. Metadata. |

`pack_text_o2r.py` reads only `msgId` and `script_pt`; the metadata columns (`mission`, `action`, `is_complete`) exist for human tracking and don't affect packing. Audio routing lives in `voice_manifest.txt` (kept in sync by hand).

### Approach
- Play through every cutscene + radio interaction, ideally one mission at a time:
  - Title screen / file select / map briefings
  - Mission radio chatter for each level: Corneria, Meteo, Sector X, Aquas, Zoness, Macbeth, Solar, Sector Y, Bolse, Fortuna, Katina, Area 6, Sector Z, Titania, Venom 1, Venom 2
  - Star Wolf encounters
  - Special rooms / cinematics / endings
- For new msgId discovery: temporarily add `fprintf(stderr, "msgId=%d\n", msgId);` at the top of `Audio_PlayVoice` in `src/audio/audio_general.c`, rebuild, redirect stderr to a log, play, then remove the printf. Append discovered msgIds to `lines.csv` with `script_pt` and `wav_file` empty until translation/recording happens.

### Done when
- Every msgId fired during a complete playthrough has a row in `lines.csv`.
- `character` is identified for every row.
- Multi-msgId voice lines are grouped under one `wav_file` (e.g., msgId=3 + msgId=1200 both → `01_que_bom.wav`, with the row using the displayable msgId — 1200 — for text override).

---

## Stage 2 — Translate the scripts

**Goal:** A pt-BR script for every line in the inventory, ready to record.

### Approach
- For each row in `lines.csv`, fill in `script_en` (from in-game observation or by decoding the original game data) — translator reference only.
- Then write `script_pt` — the pt-BR text. This single string serves as both the recording target *and* the on-screen bubble text, so write it for natural spoken delivery and use `\n` markers for radio-bubble line breaks. The packer expands `\n` to a newline glyph.

The community translation archived in `ptbr_audio/_archive/SF64 - TraducaoPT-BR.o2r` can be used as a *reference* (decode with `pack_text_o2r.py`'s glyph table in reverse) — but treat it as one opinion among many, not as canonical. The dub's voice direction diverges (already does for Pepper + Fox).

### Done when
- Every row in `lines.csv` has `script_pt` filled.

---

## Stage 3 — Recording

**Goal:** A high-quality pt-BR voice recording for every line.

### Cast
The game has ~10 distinct speaker roles. Approximate line counts (verify against the inventory):
- Fox McCloud (lots — radio chatter, level start/end, banter)
- Falco Lombardi
- Slippy Toad
- Peppy Hare
- General Pepper
- ROB 64
- Wolf, Leon, Pigma, Andrew (Star Wolf)
- Bill Grey, Katt Monroe (level-specific)
- Andross
- Misc enemies / NPCs

### Recording requirements
- Format: **32 kHz mono 16-bit PCM `.wav`** (matches Starship's internal mix rate; the WAV plays unmodified via `PlaySoundA`).
- Clean studio environment; minimal reverb (the game's BGM doesn't duck for voice — keep recordings tight).
- One file per voice line (or per logical line group when a line spans multiple msgIds).
- Filename convention: `<NN>_<short_name>.wav` where `NN` is a sequential take number — e.g. `01_que_bom.wav`, `42_falco_corneria_cleared.wav`.

### Workflow
- Engineer/developer side:
  1. Hand the cast `voice_scripts.csv` filtered to their character's lines.
  2. Receive recordings via shared drive.
  3. Per recording: drop into `ptbr_audio/`, copy to `build/x64/Release/ptbr_audio/`, add manifest entry, restart, verify in-game.

### Done when
- Every `voice_scripts.csv` row has a corresponding WAV file in `ptbr_audio/`.

---

## Stage 4 — Manifest population & QA

**Goal:** every voice line plays correctly in-game; every text bubble matches.

`lines.csv` is the master record. The text-override mod is **regenerated automatically** from it via `pack_text_o2r.py`. The voice routing manifest is **maintained by hand** alongside it (no auto-sync yet).

### Voice manifest (hand-edited)
Edit `build/x64/Release/voice_manifest.txt`:
```
<msgIds> | <letSeqRunForMsgIds> | <wavPath>
```
- `msgIds`: comma-separated. Group msgIds that share a `wav_file` in the CSV (e.g., Pepper's audio fires for both msgId=3 and msgId=1200, so the manifest row is `3, 1200`).
- `letSeqRunForMsgIds`: comma-separated subset of `msgIds` that dispatch to the seq player so the radio-click SFX plays. Engine-side note suppression in `audio_playback.c::Audio_NoteInitForLayer` allows the first 2 voice-font notes (click + opening phoneme) and mutes subsequent notes (the English voice content). Use `-` only for continuation msgIds whose sample carries no useful SFX. Most radio-chatter lines need `letSeqRunForMsgIds = <msgId>`.
- `wavPath`: `ptbr_audio/<wav_file>` — same filename as the CSV row.

### Two engine-side helpers
- **`g_dub_voice_pass_count` + `g_dub_voice_suppress_active`** (audio_general.c, audio_playback.c) — set when a `letSeqRun` msgId fires. The note-init hook decrements the counter on each voice-font NoteInit; once zero, subsequent notes get muted.
- **`CUSTOM_VOICE_PLAY_DELAY_FRAMES = 13`** (audio_general.c) — defers `PlaySoundA` by ~200 ms so the seq's click fires before our pt-BR voice. Tune this constant if the timing drifts.

### Text override mod (auto-generated)
Run `python tools/dub/pack_text_o2r.py` to regenerate `mods/SF64-DubPT-BR.o2r` from the CSV. The packer reads every row whose `msgId` and `script_pt` are non-empty.

### QA pass
- Play through every level and cutscene with the dub active.
- Listen and watch for: missing audio, wrong character, line cut off, English bleed-through, click missing, text mismatch, text overflow (forgot `\n`).
- Fix the source — `lines.csv` for text/script issues, `voice_manifest.txt` for routing issues — and repack the text mod when the CSV changes.

### Done when
- Full playthrough: all dubbed lines in pt-BR, all text matching audio, no English residue on dubbed lines, no audio glitches.
- Zero open defects in playtest notes.

---

## Stage 5 — Distribution

**Goal:** community-installable bundle.

### Bundle contents
```
SF64-DubPT-BR-v1.0.zip
├── README-pt-BR.md                  (install instructions)
├── voice_manifest.txt               (drops next to Starship.exe)
├── ptbr_audio/                      (drops next to Starship.exe)
│   └── *.wav
├── mods/
│   └── SF64-DubPT-BR.o2r            (drops into Starship's mods/ folder)
└── (engine patch instructions)      (the Audio_PlayVoice intercept needs to be in Starship's audio_general.c — until upstreamed, distribute a pre-patched Starship.exe)
```

**Optional:** include the community text-translation mod (`SF64 - TraducaoPT-BR.o2r`) so non-dubbed lines also display in pt-BR. It's archived in `ptbr_audio/_archive/`. Loads alphabetically before our mod, so dub's text overrides still win.

### Pre-distribution checklist
- [ ] All recordings normalized to consistent loudness (target -16 LUFS).
- [ ] All recordings trimmed (no silent leader/trailer beyond ~50 ms).
- [ ] License/credits file: voice cast, translators, engineering credits.
- [ ] Tested on Win10 + Win11 (the only currently supported platform).

### Upstream contribution (optional)
- Submit the `Audio_PlayVoice` manifest infrastructure as a pull request to Starship — generic enough for any future voice mod (Spanish, French, Japanese subtitles, etc.).
- Submit the two `audio_synthesis.c` bug fixes shipped during exploration:
  - `cmd++` → `aList++` typo at line 1076 (CODEC_S16 path, undeclared identifier)
  - `bytesToRead` `size_t` underflow at line 1070 (clamp to 0 when sample exhausted)

---

## Engineering follow-ups

### Cross-platform audio (priority for Linux/macOS support)
`PlaySoundA` is Win32-only. For cross-platform builds:

**Option 1 (recommended):** integrate with `libultraship`'s audio backend. `libultraship/src/audio/AudioPlayerSDL.cpp` (or equivalent) drives the existing SDL audio output. Call into that from the manifest's playback path instead of `PlaySoundA`. Pros: one audio device shared with BGM, master-volume integration, fade events. Cons: more code, requires understanding LUS audio internals.

**Option 2 (quick):** `SDL_mixer`. SDL is already linked. `Mix_LoadWAV` + `Mix_PlayChannel` is a 5-line replacement for `PlaySoundA`. Cross-platform out of the box. Cons: separate audio mix from the game (master-volume slider doesn't affect it).

### `sample_3310` crash (low priority, irrelevant for current bypass)
Tracked for completeness. If we ever revisit the engine-side sample-replacement approach, this is the first thing to debug — preferably with a real debugger (Visual Studio + the existing `Starship.pdb`) rather than printf instrumentation.

Hypotheses worth checking:
- `fontId=1 inst=7` may have a `hasTwoParts` flag or specific ADSR profile that diverges from other instruments.
- The `inst=7` instrument's three TunedSamples (low/normal/high pitch tiers) may have an unusual NULL or shared-pointer structure.
- The seq's portamento path (`audio_seqplayer.c:644`) may be the actual code path used for fontId=1 (vs the non-portamento path at line 692 used by other fonts).

### Manifest hot-reload (nice-to-have)
Currently the manifest loads once at first `Audio_PlayVoice` call. For rapid iteration during recording sessions, a debug-key (e.g. F8) that re-reads `voice_manifest.txt` would let directors swap in new takes without restarting the game. ~20 lines of code in `audio_general.c`.

### Subtitle support for cutscene-only voices (out of scope, requires engine work)
Cutscene voices like msgId=3 fire `Audio_PlayVoice` but have no associated radio-bubble text — the cutscene UI doesn't render text for them. To add pt-BR subtitles, we'd need a Starship code change to display text alongside cutscene voices. Not part of the dub project.

---

## Reference

### Working files
- `ptbr_audio/` — voice recordings (master copies)
- `build/x64/Release/ptbr_audio/` — runtime mirrors
- `build/x64/Release/voice_manifest.txt` — runtime voice routing
- `tools/dub/pack_text_o2r.py` — text packager (reads `ptbr_audio/lines.csv` directly)
- `src/audio/audio_general.c::Audio_PlayVoice` (line ~1897) — manifest loader + intercept
- `PROOF_OF_CONCEPT.md` — architecture deep-dive

### Engine source paths worth knowing
- `src/audio/audio_general.c:1850-1925` — `Audio_PlayVoice`, `Audio_UpdateVoice`, `Audio_GetCurrentVoice`
- `src/engine/fox_message.c:6-22` — `Message_IdFromPtr` (text msgPtr → msgId)
- `src/engine/fox_radio.c:128, 618` — radio voice trigger via `Message_IdFromPtr`
- `src/overlays/ovl_menu/fox_map.c:2583` — explicit `Audio_PlayVoice(3)` (Pepper cutscene)
- `assets/yaml/us/rev1/ast_radio.yaml:101` — `gMsgLookup` (780 entries)
- `tools/textconv.py:3-9` — SF64 glyph table (used by our text packager)

### External resources
- Starship: <https://github.com/HarbourMasters/Starship>
- Community translation mod (text only): `mods/SF64 - TraducaoPT-BR.o2r` in this build
- Discord: <https://discord.com/invite/shipofharkinian>

### Carry-over from earlier exploration
The `SF64RecompBRAudio` repo's `audio_dump/` decoded every voice sample from the original ROM into `.aifc`/`.wav` files. Useful as a *reference* when checking what each msgId originally said, but **the o2r path naming bears no relation to the audio-bank offsets stored there** — those notes were the wrong reference frame for Starship's resource layout. The current bypass routes by msgId only and never touches the engine's sample bank, so audio-dump path mapping is no longer needed.
