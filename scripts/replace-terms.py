import argparse
import re
from fnmatch import fnmatch
from pathlib import Path


def replace_preserve_case(text, old, new):
    def repl(match):
        word = match.group()
        if word.isupper():
            return new.upper()
        if word.islower():
            return new.lower()
        if word[0].isupper() and word[1:].islower():
            return new.capitalize()
        return new

    return re.sub(old, repl, text, flags=re.IGNORECASE)


def should_exclude(path, exclude_dirs, exclude_files):
    # Check directories in path
    for part in path.parts:
        if any(fnmatch(part, pat) for pat in exclude_dirs):
            return True

    # Check files
    if path.is_file():
        if any(fnmatch(path.name, pat) for pat in exclude_files):
            return True

    return False


def rename_path(path, old, new):
    """Rename a file or directory if it matches, preserving case."""
    new_name = replace_preserve_case(path.name, old, new)
    if new_name != path.name:
        new_path = path.with_name(new_name)
        path.rename(new_path)
        return new_path
    return path


def process_directory(
    root_dir, old, new, exclude_dirs=None, exclude_files=None, encoding="utf-8"
):
    exclude_dirs = exclude_dirs or []
    exclude_files = exclude_files or []

    root = Path(root_dir)

    # Process files and subdirectories bottom-up
    for path in sorted(root.rglob("*"), key=lambda p: -p.parts.__len__()):
        if should_exclude(path, exclude_dirs, exclude_files):
            continue
        if path.is_file():
            try:
                text = path.read_text(encoding=encoding)
            except (UnicodeDecodeError, OSError):
                continue  # skip binary/unreadable files
            new_text = replace_preserve_case(text, old, new)
            if new_text != text:
                path.write_text(new_text, encoding=encoding)
                print(f"Updated file: {path}")

        new_path = rename_path(path, old, new)
        if new_path != path:
            print(f"Renamed path: {path} -> {new_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Recursively replace terms in files and paths."
    )
    parser.add_argument("old", help="Old term to replace")
    parser.add_argument("new", help="New term to use")
    parser.add_argument("--root-dir", default=".", help="Root directory to process")
    parser.add_argument(
        "--exclude-dirs",
        nargs="*",
        default=[
            ".git",
            "node_modules",
            "dist",
            "build",
            "scripts",
            ".history",
            "__pycache__",
            "_ref",
            ".venv",
            ".next",
            "storage",
            "output",
            "data",
        ],
        help="Directory name patterns to exclude",
    )
    parser.add_argument(
        "--exclude-files",
        nargs="*",
        default=["*.pyc", "*.png", "*.jpg"],
        help="File name patterns to exclude",
    )
    parser.add_argument("--encoding", default="utf-8", help="File encoding")

    args = parser.parse_args()

    process_directory(
        root_dir=args.root_dir,
        old=args.old,
        new=args.new,
        exclude_dirs=args.exclude_dirs,
        exclude_files=args.exclude_files,
        encoding=args.encoding,
    )
