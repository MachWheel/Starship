# Star Fox 64 — Brazilian-Portuguese Dub Proof of Concept

A working **audio + text** dub of one full radio cutscene (the General-Pepper-→-Fox exchange that opens the Corneria mission briefing on the map screen) into Brazilian Portuguese. Audio plays cleanly at native rate, text matches the audio, and the cutscene's ambient SFX (radio clicks, BGM) survive untouched.

**Status: complete for one cutscene line, scaffolded for the full 779-line dub.** Voice routing is data-driven via `voice_manifest.txt`; adding a new line requires no code changes — just record a WAV, add a manifest entry, and edit the text mod.

---

## What you hear / see

When you launch the briefing on the Corneria mission select:

1. *Radio static click* (untouched, original SFX)
2. **Pepper (pt-BR):** *"Que bom que apareceram, Star Fox! Vocês são nossa única esperança."*
3. *Radio click between speakers*
4. **Fox (pt-BR):** *"Vou sentar o dedo! Dessa vez o Andross não vai se dar bem!"*
5. *Radio static click* (untouched)
6. On-screen radio bubble shows the matching pt-BR text (with accents stripped to fit SF64's font, which has no diacritic glyphs).

No English audio bleeds through. No distortion or pitch artifacts.

---

## Why this approach (and what we tried)

Starship's seq-player-driven voice channel is a phoneme assembler: it pieces a line together from short ADPCM fragments (~250 ms each) using per-instrument tuning ratios (0.25–0.34) and seq-script note durations tuned for those exact fragments. Two approaches were prototyped:

### Approach A — Sample replacement via the o2r mod system *(rejected)*

Pack pt-BR PCM into an `.o2r` mod that overrides specific `ast_audio/ast_audio_v1_sample_<HEX>` resources. Engine fixes were drafted to make `CODEC_S16` samples play correctly:

- `SampleFactory.cpp` — added `Tuning` XML attribute support (kept; harmless and useful)
- `Audio_NoteSetResamplingRate` hook — force native rate for CODEC_S16
- `Audio_ProcessNotes` extension — skip release until `samplePosInt >= endPos`
- `Audio_AllocNote` dedup — drop repeat allocations of the same active CODEC_S16 sample

It almost worked, but kept hitting the seq's design head-on:

| Blocker | What we observed |
|---|---|
| **Tuning mismatch** | Our 32 kHz mono PCM played at the seq's 0.25× rate → 4–5× slower and pitched down. The `NoteSetResamplingRate` hook fixed this. |
| **Note-duration cut-off** | Seq notes are scheduled for ~250 ms; our 5 s recording got truncated to one syllable per note. The `ProcessNotes` extension fixed this. |
| **Multi-note dispatch per line** | The seq fires multiple "phoneme replacement" notes per voice line. Even with dedup, the original note finishes before all phoneme-replacement notes fire, and later allocations restart the WAV from sample 0 — heard as `Que…Que bom…Que…`. |
| **Synthetic-wave aliasing** | `noteSub->waveSampleAddr` is a `TunedSample*` for normal notes but an `s16*` wave buffer for synthetic-wave notes. Initial hooks crashed at startup until we added `bitField1.isSyntheticWave` guards. |
| **`sample_3310` crash** | Overriding the sample on `fontId=1 inst=7` (used by msgId=1200's trailing word) reliably crashed Starship — content- and length-independent. Tracked in PLAN.md as Stage 3.5 blocker. |

The fundamental issue: the seq player was designed for ~250 ms ADPCM phoneme fragments, not 5+ second full-sentence PCM. Patching the synthesis to accommodate full-length samples kept uncovering more edge cases. The architectural mismatch is too deep to fix without rewriting the voice sequence bytecode (out of scope).

**Engine-side hooks were reverted.** Only `SampleFactory.cpp`'s `Tuning` attribute support stayed (harmless data-format extension).

### Approach B — `Audio_PlayVoice` intercept + direct WAV playback *(chosen)*

Short-circuit `Audio_PlayVoice` *before* the seq dispatcher sees the msgId. For msgIds in our manifest:
- Optionally dispatch the lead msgId to seq (`letSeqRun=msgId`) so the radio-click SFX baked into the original sample data plays. The seq fires up to 3 notes per voice msgId — click+phoneme + trailing + voice content. We let the first 2 (the click and phoneme) play and **mute** subsequent notes via an engine hook (see `audio_playback.c::Audio_NoteInitForLayer`), so the English voice content is suppressed while the click survives.
- For msgIds we don't want the click for (e.g., `msgId=1200`/`1210` continuation msgIds), set `letSeqRun=-` and skip seq dispatch entirely.
- Schedule our pt-BR WAV via Win32 `PlaySoundA` with `SND_ASYNC`, **deferred ~200 ms** (13 audio frames) so the seq's click fires *before* our voice — not after. Audio_UpdateVoice() polls each frame and fires the queued PlaySound when the delay elapses.

This works because:
- Native rate by definition (`PlaySoundA` plays the WAV unmodified)
- Full duration by definition (no seq involvement to cut it short)
- `sample_3310` crash never triggers (no XML override on the problem sample)
- SFX layer untouched (BGM, radio clicks, level audio all still go through the seq normally)
- Compatible with the seq's voice-language CVar (we run alongside, not against)
- Engine-side note suppression (`g_dub_voice_pass_count`) lets the click+phoneme through but mutes the English voice content note that follows — surgical, no audio mixing required

---

## Architecture

### Two parallel channels

```
   ┌─ msgId fired by game code (e.g., Audio_PlayVoice(1200) for Pepper)
   │
   ▼
Audio_PlayVoice (audio_general.c) ── intercept ─┐
   │                                            │
   │ (default path)                             ▼
   ▼                                ┌───────────────────────┐
Seq player → ADPCM samples →        │ Win32 PlaySoundA      │
synthesis → SDL audio out           │ ptbr_audio/*.wav      │
                                    └───────────────────────┘
                                                │
                                                ▼
                                    OS audio mixer → speakers
```

The seq player still runs (so radio clicks, BGM, and other voices that aren't dubbed yet keep working). For msgIds we've dubbed, we **either** suppress the seq dispatch entirely (so English voice stays silent) **or** let it run if the original sample data carries critical SFX (the radio click for Pepper's intro is baked into `sample_4270`'s ADPCM data).

### Text channel

Independent of audio. The community translation mod (`SF64 - TraducaoPT-BR.o2r`) already provides 779 pt-BR text messages for the radio bubble. Our mod (`SF64-DubPT-BR.o2r`) overrides just the two `gMsg_ID_<n>` entries that need to match our audio, by virtue of loading alphabetically *after* the community mod (`mFileToArchive[hash] = archive` in `libultraship/src/resource/archive/ArchiveManager.cpp:273` — last archive added wins).

---

## Files

### Source (in repo)

| Path | Purpose |
|---|---|
| `ptbr_audio/pepper/01_que_bom.wav` | Pepper's pt-BR recording (32 kHz mono 16-bit, 5.7 s) |
| `ptbr_audio/fox/01_vou_sentar_o_dedo.wav` | Fox's pt-BR recording (32 kHz mono 16-bit, 4.66 s) |
| `ptbr_audio/lines.csv` | Master dub inventory (semicolon-delimited): `msgId; mission; character; action; script_en; script_pt; wav_file; is_complete` |
| `tools/dub/pack_text_o2r.py` | Reads `lines.csv` and packs `script_pt` cells into the o2r text-override mod |
| `src/audio/audio_general.c` | `Audio_PlayVoice` intercept + custom voice table |

### Runtime (deployed alongside `Starship.exe`)

| Path | Purpose |
|---|---|
| `build/x64/Release/Starship.exe` | Built engine with the intercept compiled in |
| `build/x64/Release/ptbr_audio/pepper/01_que_bom.wav` | Mirror of the source — read at runtime by `PlaySoundA` |
| `build/x64/Release/ptbr_audio/fox/01_vou_sentar_o_dedo.wav` | Same |
| `build/x64/Release/mods/SF64-DubPT-BR.o2r` | 472 B text-override mod (gMsg_ID_1200 + 1210 in pt-BR) |
| `build/x64/Release/mods/HUD_BR_SF64.o2r` | Community HUD translation, untouched |

**Not loaded by default**: `SF64 - TraducaoPT-BR.o2r` (community text-only translation) is archived in `ptbr_audio/_archive/`. Removed from `mods/` so the development view shows English text for un-dubbed lines (matches the English audio that still plays for them, makes unprocessed lines visually obvious). Reintroduce at release if you want pt-BR text for all 779 msgIds — it loads alphabetically before our `SF64-DubPT-BR.o2r`, so our overrides still win.

The `ptbr_audio/` folder must sit next to `Starship.exe` because `PlaySoundA` resolves relative paths against the process working directory.

---

## Code anatomy

### Voice intercept (`src/audio/audio_general.c`)

The intercept reads its routing table from `ptbr_audio/voice_manifest.txt` at first call. Adding a voice line is a manifest edit, not a code change.

```c
typedef struct {
    s32 msgIds[CUSTOM_VOICE_MAX_IDS_PER_LINE];        /* 0-terminated */
    s32 letSeqRunForMsgIds[CUSTOM_VOICE_MAX_IDS_PER_LINE]; /* 0-terminated */
    char wavFile[CUSTOM_VOICE_MAX_PATH];
} CustomVoiceLine;

static CustomVoiceLine sCustomVoiceTable[CUSTOM_VOICE_MAX_LINES];
```

`Audio_PlayVoice(msgId)` walks the table, finds the row matching the firing msgId, queues the WAV path with a deferred play frame (`sCustomVoicePendingWav` + `sCustomVoicePlayAtFrame = sAudioFrameCounter + 13`), and either lets the seq run (writes `sSetNextVoiceId=true`, arms `g_dub_voice_pass_count=2` for note suppression) or returns early to mute the seq voice. `Audio_UpdateVoice()` (per-frame) fires `PlaySoundA` once the delay elapses. Any non-table msgId falls through to the original seq dispatch (so all other voices in the game still work normally).

**Two engine-side mechanisms collaborate with the intercept:**
1. **Note suppression** (`audio_playback.c::Audio_NoteInitForLayer`): when `g_dub_voice_suppress_active` is set, the first 2 NoteInit events on a voice font (fontId 0–3) pass through, subsequent ones are muted by setting `noteSub->bitField0.finished = 1; enabled = 0`. The seq's click + opening phoneme play, the main English voice content gets killed.
2. **Deferred playback** (`audio_general.c::Audio_UpdateVoice`): when `sCustomVoicePendingWav` is set, polls `sAudioFrameCounter` and fires `PlaySoundA` only after `CUSTOM_VOICE_PLAY_DELAY_FRAMES` (currently 13) audio frames have passed. Without this delay, our PlaySound would beat the seq's click by ~150 ms because `PlaySoundA` is OS-level immediate while the seq dispatch only takes effect on the next audio update tick.

### Manifest format (`voice_manifest.txt`)

```
# <msgIds> | <letSeqRunForMsgIds> | <wavPath>
3, 1200 | 3 | ptbr_audio/pepper/01_que_bom.wav
1210    | - | ptbr_audio/fox/01_vou_sentar_o_dedo.wav
```

| Field | Description |
|---|---|
| `msgIds` | Comma-separated voice msgIds that map to this WAV. Multiple msgIds let one line span multiple `Audio_PlayVoice` calls (e.g., Pepper's intro on msgId=3 + main body on msgId=1200). |
| `letSeqRunForMsgIds` | Comma-separated subset of `msgIds` that dispatch to the seq player so the radio-click SFX baked into the original sample data plays. Engine-side note suppression auto-mutes the English voice content that follows the click. Most radio-chatter lines need `letSeqRunForMsgIds = <msgId>`; use `-` only for continuation msgIds whose original sample carries no useful SFX. |
| `wavPath` | Forward-slash relative path to a 32 kHz mono 16-bit PCM `.wav`, resolved against the process working directory. |

Lines starting with `#` are comments. Whitespace is permitted around tokens. Max 1024 voice lines, 8 msgIds per line, 256-char path. The manifest is loaded once on the first `Audio_PlayVoice` call.

### Engine-side bug fixes shipped (worth upstreaming regardless of the dub)

Two bugs in `audio_synthesis.c` discovered during PoC instrumentation. Both affect the `CODEC_S16` synthesis path, which only fires for custom XML samples — so they don't manifest with stock SF64 data:

- **`audio_synthesis.c:1076`** — `aLoadBuffer(cmd++, …)` referenced an undeclared identifier `cmd`. Patched to `aLoadBuffer(aList++, …)` (matches every other call site).
- **`audio_synthesis.c:1070`** — `bytesToRead = bookSample->size - (samplePosInt * 2)` underflowed `size_t` when `samplePosInt * 2 ≥ size`, causing `aLoadBuffer` to attempt a ~4 GB read. Patched with a third branch that clamps to 0 and skips the load.

### The text override (`tools/dub/pack_text_o2r.py`)

The packer:

1. Reads `ptbr_audio/lines.csv` (semicolon-delimited). For every row with both `msgId` and `script_pt` non-empty, generates a `gMsg_ID_<msgId>` text override.
2. Expands literal `\n` in the cell to a real newline (mapped to `NWL`=1 glyph) so the radio bubble wraps properly.
3. Strips diacritics (`unicodedata.NFD` + drop `Mn` category) — SF64's font has no accented glyphs, so *você* → *voce*. The community translation team did the same.
4. Maps each character to its index in SF64's `char_code[]` table (lifted from `tools/textconv.py:3-9`). Special codes: `END`=0, `NWL`=1 (newline), `SPC`=12 (space).
5. Wraps the glyph stream in the LUS resource header layout:
   - 64-byte OTR header: `byteOrder=0` (LE), `isCustom=0` (matches existing translations), `Type=0x4D534720` (`'MSG '` per `src/port/resource/type/ResourceType.h:10`), `Version=0`, `Id=0xDEADBEEFDEADBEEF` (default), padding.
   - Payload: `uint32 size` + `size × uint16` glyph indices.
6. Packs each `gMsg_ID_<n>` entry into a ZIP at `ast_radio/gMsg_ID_<n>` with DEFLATE compression (matches `sf64.o2r`).

The XML format auto-detection in `libultraship/src/resource/ResourceLoader.cpp:88` only triggers on a leading `<` byte, so binary resources like ours fall through to `ReadResourceInitDataLegacy` which parses the OTR header.

---

## How to extend the dub

### Add another character's line

1. **Record** the pt-BR audio at 32 kHz mono 16-bit PCM. Drop into `ptbr_audio/<descriptive_name>.wav`. Copy to `build/x64/Release/ptbr_audio/` for runtime.
2. **Find the msgIds.** When the line is fired by `Radio_PlayMessage(gMsg_ID_<n>, RCID_<character>)` (most radio chatter), only `<n>` is needed. For cutscene-driven lines like Pepper's that span multiple `Audio_PlayVoice` calls, temporarily drop `fprintf(stderr, "msgId=%d\n", msgId);` at the top of `Audio_PlayVoice` (`src/audio/audio_general.c`), rebuild, replay the cutscene with stderr redirected to a log, and read off every voice fire in order. Use the **displayable** msgId in `lines.csv` (the one whose text shows in the radio bubble); use **all involved msgIds** in `voice_manifest.txt`.
3. **Add a row** to `ptbr_audio/lines.csv` (semicolon-delimited):
   ```
   <msgId>;<character>;<script_en>;<script_pt with \n line breaks>;<wav_file>
   ```
4. **Add a row** to `ptbr_audio/voice_manifest.txt` (and sync into `build/x64/Release/ptbr_audio/`):
   ```
   <msgIds> | <letSeqRunForMsgIds> | <wavPath>
   ```
   Most lines need `-` in the `letSeqRunForMsgIds` field. Only list a msgId there if the original sample for that msgId carries an SFX (radio click) you want to preserve.
5. **Re-pack the text mod:** `python tools/dub/pack_text_o2r.py` (reads the CSV).
6. **Restart Starship** — no rebuild needed. The voice manifest reloads at the first `Audio_PlayVoice` call.

### Replace an existing dub recording

Drop the new WAV into `ptbr_audio/` (and the runtime mirror), update the manifest's `wavPath`, restart. **No** rebuild needed.

---

## Known limitations / follow-ups

| Issue | Impact | Tracked in |
|---|---|---|
| `sample_3310` override crashes Starship | Forced us into the bypass architecture; not a problem unless someone tries the sample-replacement path again | PLAN.md → "Outstanding blockers" |
| `PlaySoundA` is Win32-only | Linux/Mac builds need a different audio path (SDL_mixer, libultraship's audio backend, etc.) | Future cross-platform port |
| Single concurrent WAV | `PlaySoundA` plays one sound at a time; if a non-dubbed voice plays during a dubbed one, the new dubbed one cuts the previous off. Acceptable for cutscenes (one speaker at a time) | Acceptable for current scope |
| SF64 font has no accents | Source text in `lines.csv` `script_pt` may be written with diacritics but on-screen text loses them at pack time | Would need a font extension to fix |
| Pitch/duration mismatch issue | Doesn't apply to the bypass path (PlaySound plays at native rate), but blocks the in-engine sample-replacement path | PLAN.md → "Tuning mismatch" |

---

## Recap of working files & where to find them

```
C:\Repos\Starship\
├── ptbr_audio\
│   ├── lines.csv                                  ← Master dub inventory (text packer reads from this)
│   ├── pepper\
│   │   └── 01_que_bom.wav                         ← Pepper master recording
│   ├── fox\
│   │   └── 01_vou_sentar_o_dedo.wav               ← Fox master recording
│   └── _archive\
│       └── SF64 - TraducaoPT-BR.o2r               ← Community text-only translation (not loaded; reference)
├── tools\dub\
│   └── pack_text_o2r.py                           ← Text packager (reads ptbr_audio/lines.csv)
├── src\audio\
│   ├── audio_general.c (modified)                 ← Voice intercept + manifest loader + deferred PlaySound
│   └── audio_playback.c (modified)                ← Voice-content note suppression hook
├── src\port\resource\importers\audio\
│   └── SampleFactory.cpp (modified)               ← Tuning XML attribute support
├── PLAN.md                                        ← Plan for completing the full dub
├── PROOF_OF_CONCEPT.md                            ← This file
└── build\x64\Release\
    ├── Starship.exe                               ← Built engine
    ├── ptbr_audio\
    │   ├── voice_manifest.txt                     ← Voice routing manifest (hand-edited)
    │   └── <character>\*.wav                      ← Runtime mirrors (per-character subfolders)
    └── mods\
        ├── SF64-DubPT-BR.o2r                      ← Generated text override (from lines.csv)
        └── HUD_BR_SF64.o2r                        ← Community HUD (untouched)
```

## Path to the full 779-line dub

Engineering-wise, scaling from 1 to 779 lines is one-line-per-line in two manifests + one WAV recording per line. No new code paths. The remaining work is creative (recording 779 voice lines with native pt-BR speakers) and editorial (matching pt-BR translations for the radio bubble text).

**Cross-platform port:** `PlaySoundA` is Win32-only. Linux/macOS builds will need a different audio backend — the cleanest path is integrating with `libultraship/src/audio/AudioPlayer*` (SDL or platform-specific). Marked as a follow-up in `tools/dub/`'s TODO when those targets become priorities.

**`sample_3310` crash:** Tracked in PLAN.md → Stage 3.5. Currently irrelevant (the bypass avoids it entirely), but worth resolving if someone wants the engine-side approach to work in the future.
