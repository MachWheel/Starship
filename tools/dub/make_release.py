"""Stage and zip a Windows release bundle for the SF64 pt-BR voice dub.

Reads inputs from this repo and produces:

    release/SF64-DubPT-BR-v<version>-windows.zip

Bundle layout (matches PLAN.md Stage 5):

    Starship.exe                       patched build with dub intercept
    voice_manifest.txt                 hand-edited manifest
    ptbr_audio/<character>/*.wav       voice recordings (only those referenced
                                       by the manifest are bundled)
    mods/SF64-DubPT-BR.o2r             text override mod
    LICENSE-libultraship.txt           MIT, required when redistributing
    README.md                          install instructions (en + pt)
    CREDITS.md                         voice cast, translation, engineering

Run this AFTER:
    1. `python tools/dub/pack_text_o2r.py` (text mod regenerated from CSV)
    2. A fresh release build (`build_starship.bat`)

The script never touches the manifest. Edit voice_manifest.txt by hand before
running this.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import zipfile
from pathlib import Path

REPO_ROOT = Path(r"C:\Repos\Starship")
RELEASE_TEMPLATES = REPO_ROOT / "release-templates"

EXE_SRC = REPO_ROOT / "build" / "x64" / "Release" / "Starship.exe"
MANIFEST_SRC = REPO_ROOT / "build" / "x64" / "Release" / "voice_manifest.txt"
TEXT_MOD_SRC = REPO_ROOT / "build" / "x64" / "Release" / "mods" / "SF64-DubPT-BR.o2r"
PTBR_AUDIO_SRC = REPO_ROOT / "ptbr_audio"
LIBULTRASHIP_LICENSE = REPO_ROOT / "libultraship" / "LICENSE"
COMMUNITY_TEXT_MOD = PTBR_AUDIO_SRC / "_archive" / "SF64 - TraducaoPT-BR.o2r"
README_TEMPLATE = RELEASE_TEMPLATES / "README.md"
CREDITS_TEMPLATE = RELEASE_TEMPLATES / "CREDITS.md"


def _verify_inputs() -> list[str]:
    errs: list[str] = []
    for p in (EXE_SRC, MANIFEST_SRC, TEXT_MOD_SRC, LIBULTRASHIP_LICENSE,
              README_TEMPLATE, CREDITS_TEMPLATE):
        if not p.exists():
            errs.append(f"missing: {p}")
    return errs


def _parse_manifest_wavs(manifest_path: Path) -> list[str]:
    """Returns wav paths from the manifest, relative to ptbr_audio/."""
    wavs: list[str] = []
    seen: set[str] = set()
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        wav_field = parts[2]
        if not wav_field.startswith("ptbr_audio/"):
            continue
        rel = wav_field[len("ptbr_audio/"):]
        if rel in seen:
            continue
        seen.add(rel)
        wavs.append(rel)
    return wavs


def _stage(stage_dir: Path, version: str, include_community: bool) -> None:
    stage_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(EXE_SRC, stage_dir / "Starship.exe")
    shutil.copy2(MANIFEST_SRC, stage_dir / "voice_manifest.txt")

    mods_dir = stage_dir / "mods"
    mods_dir.mkdir(exist_ok=True)
    shutil.copy2(TEXT_MOD_SRC, mods_dir / "SF64-DubPT-BR.o2r")

    if include_community:
        if COMMUNITY_TEXT_MOD.exists():
            shutil.copy2(COMMUNITY_TEXT_MOD, mods_dir / COMMUNITY_TEXT_MOD.name)
            print(f"  + bundled community text mod: {COMMUNITY_TEXT_MOD.name}")
        else:
            print(f"  WARNING: --include-community-mod set but {COMMUNITY_TEXT_MOD} not found", file=sys.stderr)

    wavs = _parse_manifest_wavs(MANIFEST_SRC)
    missing: list[str] = []
    for wav in wavs:
        src = PTBR_AUDIO_SRC / wav
        if not src.exists():
            missing.append(wav)
            continue
        dst = stage_dir / "ptbr_audio" / wav
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    print(f"  + {len(wavs) - len(missing)} WAV(s) bundled")
    if missing:
        print("  WARNING: source WAVs missing for these manifest entries:", file=sys.stderr)
        for m in missing:
            print(f"    - {m}", file=sys.stderr)

    shutil.copy2(LIBULTRASHIP_LICENSE, stage_dir / "LICENSE-libultraship.txt")

    readme = README_TEMPLATE.read_text(encoding="utf-8").replace("{{VERSION}}", version)
    (stage_dir / "README.md").write_text(readme, encoding="utf-8")

    credits = CREDITS_TEMPLATE.read_text(encoding="utf-8").replace("{{VERSION}}", version)
    (stage_dir / "CREDITS.md").write_text(credits, encoding="utf-8")


def _zip(stage_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(stage_dir.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(stage_dir))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", default="0.1.0",
                    help="Release version, used in zip filename and templates. Default: 0.1.0")
    ap.add_argument("--include-community-mod", action="store_true",
                    help="Bundle the community pt-BR text translation as a fallback for non-dubbed lines.")
    ap.add_argument("--output-dir", type=Path, default=REPO_ROOT / "release",
                    help="Where to stage and zip. Default: ./release/")
    args = ap.parse_args()

    errs = _verify_inputs()
    if errs:
        print("Pre-flight checks failed:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 1

    bundle_name = f"SF64-DubPT-BR-v{args.version}-windows"
    stage_dir = args.output_dir / bundle_name
    zip_path = args.output_dir / f"{bundle_name}.zip"

    if stage_dir.exists():
        shutil.rmtree(stage_dir)

    print(f"=== building {bundle_name} ===\n")
    print(f"[1/2] staging to {stage_dir}...")
    _stage(stage_dir, args.version, args.include_community_mod)
    file_count = sum(1 for _ in stage_dir.rglob("*") if _.is_file())
    print(f"  staged {file_count} file(s) total\n")

    print(f"[2/2] zipping to {zip_path}...")
    _zip(stage_dir, zip_path)
    size_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"  wrote {zip_path} ({size_mb:.2f} MB)\n")

    print("Done. Upload the zip to a GitHub Release on MachWheel/Starship.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
