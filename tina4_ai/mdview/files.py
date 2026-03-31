"""File browser API — list directories and read .md files."""

from pathlib import Path

SKIP_DIRS = frozenset({
    ".git", "__pycache__", "node_modules", "vendor", ".venv",
    "venv", "dist", "build", ".tox", ".mypy_cache", ".pytest_cache",
    ".idea", ".vscode", ".DS_Store", "egg-info",
})


def _is_skipped(name: str) -> bool:
    if name.startswith("."):
        return True
    return any(skip in name for skip in SKIP_DIRS)


def count_md_files(directory: Path) -> int:
    """Recursively count .md files in a directory."""
    count = 0
    try:
        for entry in directory.iterdir():
            if _is_skipped(entry.name):
                continue
            if entry.is_file() and entry.suffix.lower() == ".md":
                count += 1
            elif entry.is_dir():
                count += count_md_files(entry)
    except PermissionError:
        pass
    return count


def list_entries(directory: Path, project_root: Path) -> list[dict]:
    """List directory entries: dirs with .md files + .md files."""
    entries = []
    try:
        items = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return entries

    for item in items:
        if _is_skipped(item.name):
            continue

        rel_path = str(item.relative_to(project_root))

        if item.is_dir():
            md_count = count_md_files(item)
            if md_count > 0:
                entries.append({
                    "name": item.name,
                    "type": "dir",
                    "path": rel_path,
                    "md_count": md_count,
                })
        elif item.is_file() and item.suffix.lower() == ".md":
            stat = item.stat()
            entries.append({
                "name": item.name,
                "type": "file",
                "path": rel_path,
                "size": stat.st_size,
            })

    return entries


def read_file(file_path: Path, project_root: Path) -> dict | None:
    """Read a .md file, returning its content and metadata.

    Returns None if the file is outside project root, not .md, or too large.
    """
    resolved = file_path.resolve()
    root_resolved = project_root.resolve()

    # Path traversal check
    if not str(resolved).startswith(str(root_resolved)):
        return None

    # Extension check
    if resolved.suffix.lower() != ".md":
        return None

    # Existence check
    if not resolved.is_file():
        return None

    # Size check (1MB limit)
    size = resolved.stat().st_size
    if size > 1_048_576:
        return None

    content = resolved.read_text(encoding="utf-8", errors="replace")
    rel_path = str(resolved.relative_to(root_resolved))

    return {
        "content": content,
        "path": rel_path,
        "size": size,
    }


def validate_path(requested: str, project_root: Path) -> Path | None:
    """Resolve a requested path safely within the project root.

    Returns the resolved Path or None if it escapes the root.
    """
    target = (project_root / requested).resolve()
    if not str(target).startswith(str(project_root.resolve())):
        return None
    return target
