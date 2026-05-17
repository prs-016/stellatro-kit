import argparse
import re
import zipfile
from pathlib import Path


STARTER_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_DIR = STARTER_ROOT / "submission_folder"
DEFAULT_OUTPUT_DIR = STARTER_ROOT / "submission_zips"
EXCLUDED_PARTS = {
    ".pytest_cache",
    "__pycache__",
}
EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def safe_zip_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", name.strip())
    cleaned = cleaned.strip(".-")
    if not cleaned:
        raise ValueError("Submission name must include at least one letter or number.")
    return cleaned


def should_include(path: Path) -> bool:
    if any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    return path.suffix not in EXCLUDED_SUFFIXES


def zip_submission(source_dir: Path, output_dir: Path, submission_name: str) -> Path:
    source_dir = source_dir.resolve()
    output_dir = output_dir.resolve()

    if not source_dir.is_dir():
        raise FileNotFoundError(f"Submission folder not found: {source_dir}")
    if not (source_dir / "bot.py").is_file():
        raise FileNotFoundError(f"Submission folder must contain bot.py: {source_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f"{safe_zip_name(submission_name)}.zip"

    files = [
        path
        for path in source_dir.rglob("*")
        if path.is_file() and should_include(path.relative_to(source_dir))
    ]
    if not files:
        raise RuntimeError(f"No files found to package in {source_dir}")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            archive.write(path, path.relative_to(source_dir).as_posix())

    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Zip starter-kit/submission_folder for portal submission."
    )
    parser.add_argument("name", help="Output zip name, without .zip")
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="Folder to package. Defaults to starter-kit/submission_folder.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Where to write the zip. Defaults to starter-kit/submission_zips.",
    )
    args = parser.parse_args()

    zip_path = zip_submission(args.source, args.output_dir, args.name)
    print(f"Created {zip_path}")


if __name__ == "__main__":
    main()
