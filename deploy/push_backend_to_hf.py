"""
Uploads the backend/ folder to a Hugging Face Docker Space.

Usage (from the repo root, after `huggingface-cli login`):
    backend/.venv/Scripts/python.exe deploy/push_backend_to_hf.py <user>/<space-name>
    backend/.venv/Scripts/python.exe deploy/push_backend_to_hf.py <user>/<space-name> --dry-run

Only code, requirements, the Dockerfile and the YOLO weights are sent.
Secrets (.env), patient photos (uploads/), backups, test databases and the
virtualenv are never uploaded. Large weight files go through Git LFS
automatically (huggingface_hub handles that).
"""
from __future__ import annotations

import argparse
import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
SPACE_README = ROOT / "deploy" / "hf_space_README.md"

IGNORE = [
    ".env", ".env.*", "uploads/*", "backups/*", "test.db", "test_artifacts/*",
    "app/ml/artifacts/*", ".venv/*", "venv/*", "*__pycache__*", "*.pyc",
    ".pytest_cache/*", "training/*", "tests/*", "load_test.py",
    "reset_test_data.py", "test_reset_roundtrip.py", "README.md",
    "models_weights/*.onnx*", "requirements-prod.txt",
]


def files_to_upload() -> list[Path]:
    out = []
    for path in BACKEND.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(BACKEND).as_posix()
        if rel == ".env.example" or not any(fnmatch.fnmatch(rel, pat) for pat in IGNORE):
            out.append(path)
    return sorted(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("space", help="Space id, e.g. codismile/toothwise-api")
    parser.add_argument("--dry-run", action="store_true", help="List files without uploading")
    args = parser.parse_args()

    files = files_to_upload()
    total_mb = sum(f.stat().st_size for f in files) / 1e6
    for f in files:
        print(f"  {f.relative_to(BACKEND).as_posix()}")
    print(f"{len(files)} files, {total_mb:.1f} MB, plus README.md (Space config)")
    for rel in (f.relative_to(BACKEND).as_posix() for f in files):
        if rel.startswith(("uploads/", "backups/")) or rel == ".env":
            raise SystemExit(f"Refusing to upload sensitive file: {rel}")
    if args.dry_run:
        return

    from huggingface_hub import HfApi

    api = HfApi()
    api.upload_folder(
        folder_path=str(BACKEND),
        repo_id=args.space,
        repo_type="space",
        ignore_patterns=IGNORE,
        allow_patterns=None,
        commit_message="Deploy ToothWise backend",
    )
    api.upload_file(
        path_or_fileobj=str(SPACE_README),
        path_in_repo="README.md",
        repo_id=args.space,
        repo_type="space",
        commit_message="Space configuration",
    )
    print(f"Uploaded. Build log: https://huggingface.co/spaces/{args.space}?logs=build")


if __name__ == "__main__":
    main()
