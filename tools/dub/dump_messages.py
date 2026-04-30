"""Dump all gMsg_ID_<n> entries from an .o2r asset pack as decoded text.

Reverse of pack_text_o2r.py: reads the o2r as a zip, parses the OTR header,
decodes the glyph payload back to ASCII, and prints `<msgId>: <text>` for
every message resource. Used to discover msgIds for new lines.csv rows by
matching English text.
"""

from __future__ import annotations

import argparse
import struct
import sys
import zipfile
from pathlib import Path

SF64_CHAR_CODE = [
    "END","NWL","NP2","NP3","NP4","NP5","NP6","NP7","NP8","NP9","NPA","NPB","SPC","HSP","QSP","NPF",
    "CLF","CUP","CRT","CDN","AUP","ALF","ADN","ART",
    "_A","_B","_C","_D","_E","_F","_G","_H","_I","_J","_K","_L","_M","_N","_O","_P","_Q","_R","_S","_T","_U","_V","_W","_X","_Y","_Z",
    "_a","_b","_c","_d","_e","_f","_g","_h","_i","_j","_k","_l","_m","_n","_o","_p","_q","_r","_s","_t","_u","_v","_w","_x","_y","_z",
    "EXM","QST","DSH","CMA","PRD","_0","_1","_2","_3","_4","_5","_6","_7","_8","_9","APS","LPR","RPR","CLN","PIP",
]

GLYPH_TO_CHAR: dict[int, str] = {}
for idx, code in enumerate(SF64_CHAR_CODE):
    if code.startswith("_") and len(code) == 2:
        GLYPH_TO_CHAR[idx] = code[1]
GLYPH_TO_CHAR.update({
    0: "",       # END
    1: "\\n",    # NWL (rendered as literal \n for grep-friendliness)
    12: " ",     # SPC
    13: " ",     # QSP
    14: " ",     # HSP
    15: "|",     # NXT
    16: "(C-LF)",
    17: "(C-UP)",
    18: "(C-RT)",
    19: "(C-DN)",
    20: "(AUP)",
    21: "(ALF)",
    22: "(ADN)",
    23: "(ART)",
    76: "!",
    77: "?",
    78: "-",
    79: ",",
    80: ".",
    91: "'",
    92: "(",
    93: ")",
    94: ":",
    95: "|",
})

OTR_HEADER_SIZE = 64


def decode_message(data: bytes) -> str | None:
    if len(data) < OTR_HEADER_SIZE + 4:
        return None
    payload = data[OTR_HEADER_SIZE:]
    (size,) = struct.unpack_from("<I", payload, 0)
    if 4 + size * 2 > len(payload):
        return None
    glyphs = struct.unpack_from(f"<{size}H", payload, 4)
    out: list[str] = []
    for g in glyphs:
        if g == 0:
            break
        out.append(GLYPH_TO_CHAR.get(g, f"<{g}>"))
    return "".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--o2r", type=Path, default=Path(r"C:\Repos\Starship\build\x64\Release\sf64.o2r"))
    ap.add_argument("--filter", help="Only show msgIds whose text contains this substring (case-insensitive).")
    ap.add_argument("--id-range", help="Only show msgIds in this range, e.g. '2000-2999'.")
    args = ap.parse_args()

    lo, hi = (None, None)
    if args.id_range:
        a, b = args.id_range.split("-", 1)
        lo, hi = int(a), int(b)

    with zipfile.ZipFile(args.o2r) as zf:
        entries = [name for name in zf.namelist() if name.startswith("ast_radio/gMsg_ID_")]
        rows: list[tuple[int, str]] = []
        for name in entries:
            try:
                msg_id = int(name.rsplit("_", 1)[1])
            except ValueError:
                continue
            if lo is not None and not (lo <= msg_id <= hi):
                continue
            data = zf.read(name)
            text = decode_message(data)
            if text is None:
                continue
            if args.filter and args.filter.lower() not in text.lower():
                continue
            rows.append((msg_id, text))

    rows.sort()
    for msg_id, text in rows:
        print(f"{msg_id}: {text}")
    print(f"\n{len(rows)} message(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
