"""Warn about .wav files under ptbr_audio/ that aren't referenced by voice_manifest.txt.

Catches dub recordings that were saved but forgotten in the manifest — those
would never play in-game and wouldn't be bundled by `make_release.py`.

Read-only: this tool never writes the manifest or moves files. Complements
`make_release.py`, which already warns about the inverse case (manifest entries
pointing to missing wavs).

Usage:
    python tools/dub/find_orphan_wavs.py

Exit code is 0 when every wav on disk is referenced, 1 otherwise — handy to
gate a pre-commit hook or release build.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PTBR_AUDIO = REPO_ROOT / "ptbr_audio"
MANIFEST = PTBR_AUDIO / "voice_manifest.txt"
EXCLUDE_DIRS = {"_archive"}


def parse_manifest_wavs(manifest_path: Path) -> set[str]:
    """Wav paths (forward-slash, including the `ptbr_audio/` prefix) referenced by the manifest."""
    referenced: set[str] = set()
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        wav_field = parts[2]
        if wav_field.startswith("ptbr_audio/"):
            referenced.add(wav_field)
    return referenced


def find_disk_wavs(audio_root: Path) -> set[str]:
    """Wav paths on disk (forward-slash, including the `ptbr_audio/` prefix), excluding archive dirs."""
    on_disk: set[str] = set()
    repo_root = audio_root.parent
    for p in audio_root.rglob("*.wav"):
        rel_to_audio = p.relative_to(audio_root).parts
        if any(part in EXCLUDE_DIRS for part in rel_to_audio):
            continue
        on_disk.add(p.relative_to(repo_root).as_posix())
    return on_disk


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--manifest", type=Path, default=MANIFEST,
                    help=f"Manifest path. Default: {MANIFEST}")
    ap.add_argument("--audio-root", type=Path, default=PTBR_AUDIO,
                    help=f"Audio root scanned for wavs. Default: {PTBR_AUDIO}")
    args = ap.parse_args()

    if not args.manifest.exists():
        print(f"ERROR: manifest not found: {args.manifest}", file=sys.stderr)
        return 2
    if not args.audio_root.exists():
        print(f"ERROR: audio root not found: {args.audio_root}", file=sys.stderr)
        return 2

    referenced = parse_manifest_wavs(args.manifest)
    on_disk = find_disk_wavs(args.audio_root)
    orphans = sorted(on_disk - referenced)

    if not orphans:
        print(f"OK: all {len(on_disk)} wav(s) under {args.audio_root.name}/ are referenced by the manifest.")
        return 0

    print(f"WARNING: {len(orphans)} orphan wav(s) under {args.audio_root.name}/ not referenced by the manifest:",
          file=sys.stderr)
    for w in orphans:
        print(f"  {w}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
