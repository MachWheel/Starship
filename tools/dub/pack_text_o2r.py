"""Pack pt-BR text overrides into an .o2r mod for Starship.

Reads `ptbr_audio/lines.csv` (the master dub inventory) and emits a binary
.o2r mod overriding `ast_radio/gMsg_ID_<n>` resources for every row where
`ptbr_display_text` is non-empty. Text is encoded into SF64's glyph table
(lifted from `tools/textconv.py`) and wrapped in the LUS resource header
layout (64-byte OTR header + uint32 size + size×u16 glyphs).

Layout produced inside the o2r:
    ast_radio/gMsg_ID_<n>   binary resource: OTR header + payload

Resource format reverse-engineered from:
  - libultraship/src/resource/ResourceLoader.cpp:85-123 (legacy binary header)
  - libultraship/src/resource/ResourceLoader.cpp:238-274 (header parser)
  - src/port/resource/importers/MessageFactory.cpp (binary message factory)
  - src/port/resource/type/ResourceType.h:10 (Message = 0x4D534720 'MSG ')

SF64's font is plain ASCII — no accented glyphs. Accents are stripped before
encoding (matches what the existing community translation team did). Literal
"\\n" in the CSV cell is expanded to a newline glyph (NWL=1). Button-icon
escape sequences "(C-LF)", "(C-UP)", "(C-RT)", "(C-DN)", "(AUP)", "(ALF)",
"(ADN)", "(ART)" map to their corresponding glyph indices (16-23) — same
syntax dump_messages.py emits, so round-trip is symmetric.
"""

from __future__ import annotations

import argparse
import csv
import struct
import sys
import unicodedata
import zipfile
from pathlib import Path


SF64_CHAR_CODE = [
    "END","NWL","NP2","NP3","NP4","NP5","NP6","NP7","NP8","NP9","NPA","NPB","SPC","HSP","QSP","NPF",
    "CLF","CUP","CRT","CDN","AUP","ALF","ADN","ART",
    "_A","_B","_C","_D","_E","_F","_G","_H","_I","_J","_K","_L","_M","_N","_O","_P","_Q","_R","_S","_T","_U","_V","_W","_X","_Y","_Z",
    "_a","_b","_c","_d","_e","_f","_g","_h","_i","_j","_k","_l","_m","_n","_o","_p","_q","_r","_s","_t","_u","_v","_w","_x","_y","_z",
    "EXM","QST","DSH","CMA","PRD","_0","_1","_2","_3","_4","_5","_6","_7","_8","_9","APS","LPR","RPR","CLN","PIP",
]

CHAR_TO_GLYPH: dict[str, int] = {}
for idx, code in enumerate(SF64_CHAR_CODE):
    if code.startswith("_") and len(code) == 2:
        CHAR_TO_GLYPH[code[1]] = idx

CHAR_TO_GLYPH.update({
    " ": 12,    # SPC
    "\n": 1,    # NWL
    "!": 76,    # EXM
    "?": 77,    # QST
    "-": 78,    # DSH
    ",": 79,    # CMA
    ".": 80,    # PRD
    "'": 91,    # APS
    "(": 92,    # LPR
    ")": 93,    # RPR
    ":": 94,    # CLN
    "|": 15,    # NXT (next text box) — matches dump_messages.py
})

SPECIAL_GLYPHS: dict[str, int] = {
    "(C-LF)": 16, "(C-UP)": 17, "(C-RT)": 18, "(C-DN)": 19,
    "(AUP)":  20, "(ALF)":  21, "(ADN)":  22, "(ART)":  23,
    "(NXT)":  15,
}

RESOURCE_TYPE_MESSAGE = 0x4D534720  # 'MSG '
OTR_HEADER_SIZE = 64


def strip_accents(s: str) -> str:
    """SF64's font has no accented glyphs; strip diacritics so 'você' → 'voce'."""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def encode_text(text: str) -> list[int]:
    """ASCII (post-accent-strip) → glyph indices, terminated with END (0)."""
    glyphs: list[int] = []
    skipped: list[str] = []
    text = strip_accents(text)
    i = 0
    while i < len(text):
        special = next((seq for seq in SPECIAL_GLYPHS if text.startswith(seq, i)), None)
        if special is not None:
            glyphs.append(SPECIAL_GLYPHS[special])
            i += len(special)
            continue
        ch = text[i]
        g = CHAR_TO_GLYPH.get(ch)
        if g is None:
            skipped.append(ch)
        else:
            glyphs.append(g)
        i += 1
    if skipped:
        print(f"  WARNING: dropped {len(skipped)} unencodable char(s): {skipped!r}", file=sys.stderr)
    glyphs.append(0)  # END terminator
    return glyphs


def build_otr_header() -> bytes:
    """Match the byteOrder=0 / isCustom=0 layout used by `SF64 - TraducaoPT-BR.o2r`."""
    hdr = bytearray(OTR_HEADER_SIZE)
    hdr[0] = 0  # byteOrder = native LE
    hdr[1] = 0  # isCustom = false (matches existing translations)
    struct.pack_into("<I", hdr, 4, RESOURCE_TYPE_MESSAGE)
    struct.pack_into("<I", hdr, 8, 0)  # version
    struct.pack_into("<Q", hdr, 12, 0xDEADBEEFDEADBEEF)  # default Id
    return bytes(hdr)


def build_message_resource(glyphs: list[int]) -> bytes:
    """OTR header (64 B) + uint32 size + size×uint16 glyphs."""
    payload = struct.pack("<I", len(glyphs)) + struct.pack(f"<{len(glyphs)}H", *glyphs)
    return build_otr_header() + payload


def pack(csv_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    seen_msg_ids: set[int] = set()

    with csv_path.open("r", encoding="utf-8", newline="") as f, \
         zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        reader = csv.DictReader(f, delimiter=";")
        for row_num, row in enumerate(reader, start=2):  # row 1 is header
            text = (row.get("script_pt") or "").strip()
            msg_id_str = (row.get("msgId") or "").strip()
            # Empty msgId rows are placeholders for not-yet-mapped lines; skip silently.
            if not msg_id_str:
                continue
            if not text:
                continue
            try:
                msg_id = int(msg_id_str)
            except ValueError:
                print(f"  WARNING: row {row_num}: invalid msgId={msg_id_str!r}; skipping", file=sys.stderr)
                continue
            if msg_id in seen_msg_ids:
                print(f"  WARNING: row {row_num}: duplicate msgId={msg_id}; later row wins", file=sys.stderr)
            seen_msg_ids.add(msg_id)

            # Expand literal "\n" in the CSV cell to a real newline so
            # encode_text maps it to NWL.
            text = text.replace("\\n", "\n")
            glyphs = encode_text(text)
            data = build_message_resource(glyphs)
            archive_path = f"ast_radio/gMsg_ID_{msg_id}"
            out.writestr(archive_path, data)
            written += 1
            preview = strip_accents(text).replace("\n", "\\n")
            speaker = row.get("character", "?")
            print(f"  msgId={msg_id} ({speaker}) -> {archive_path} ({len(data)} B, {len(glyphs)} glyphs): {preview!r}")

    print(f"\nWrote {output_path} ({output_path.stat().st_size:,} bytes, {written} message override{'' if written == 1 else 's'})")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--csv",
        type=Path,
        default=Path(r"C:\Repos\Starship\ptbr_audio\lines.csv"),
        help="Master dub inventory CSV (msgId, speaker, ptbr_display_text, ...).",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=Path(r"C:\Repos\Starship\build\x64\Release\mods\SF64-DubPT-BR.o2r"),
    )
    args = ap.parse_args()
    pack(args.csv, args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
