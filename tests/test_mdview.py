"""Tests for tina4_ai.mdview."""

import tempfile
from pathlib import Path

from tina4_ai.mdview.files import count_md_files, list_entries, read_file, validate_path
from tina4_ai.mdview.viewer import build_html


class TestValidatePath:
    def test_valid_path(self, tmp_path):
        (tmp_path / "README.md").touch()
        result = validate_path("README.md", tmp_path)
        assert result is not None
        assert result == (tmp_path / "README.md").resolve()

    def test_traversal_blocked(self, tmp_path):
        result = validate_path("../../etc/passwd", tmp_path)
        assert result is None

    def test_dot_path(self, tmp_path):
        result = validate_path(".", tmp_path)
        assert result == tmp_path.resolve()

    def test_nested_path(self, tmp_path):
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "guide.md").touch()
        result = validate_path("docs/guide.md", tmp_path)
        assert result is not None


class TestCountMdFiles:
    def test_counts_md_files(self, tmp_path):
        (tmp_path / "a.md").touch()
        (tmp_path / "b.md").touch()
        (tmp_path / "c.txt").touch()
        assert count_md_files(tmp_path) == 2

    def test_counts_recursively(self, tmp_path):
        (tmp_path / "a.md").touch()
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.md").touch()
        assert count_md_files(tmp_path) == 2

    def test_skips_hidden_dirs(self, tmp_path):
        hidden = tmp_path / ".git"
        hidden.mkdir()
        (hidden / "notes.md").touch()
        assert count_md_files(tmp_path) == 0

    def test_skips_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "readme.md").touch()
        assert count_md_files(tmp_path) == 0


class TestListEntries:
    def test_lists_md_files_and_dirs(self, tmp_path):
        (tmp_path / "README.md").write_text("# Hello")
        (tmp_path / "notes.txt").touch()
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "guide.md").touch()

        entries = list_entries(tmp_path, tmp_path)
        names = [e["name"] for e in entries]
        assert "docs" in names
        assert "README.md" in names
        assert "notes.txt" not in names

    def test_dirs_first(self, tmp_path):
        (tmp_path / "z.md").touch()
        sub = tmp_path / "a_dir"
        sub.mkdir()
        (sub / "x.md").touch()

        entries = list_entries(tmp_path, tmp_path)
        assert entries[0]["type"] == "dir"
        assert entries[1]["type"] == "file"

    def test_excludes_empty_dirs(self, tmp_path):
        (tmp_path / "empty").mkdir()
        (tmp_path / "readme.md").touch()

        entries = list_entries(tmp_path, tmp_path)
        names = [e["name"] for e in entries]
        assert "empty" not in names


class TestReadFile:
    def test_reads_md_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("# Test\nHello world")

        result = read_file(f, tmp_path)
        assert result is not None
        assert result["content"] == "# Test\nHello world"
        assert result["path"] == "test.md"

    def test_rejects_non_md(self, tmp_path):
        f = tmp_path / "test.py"
        f.write_text("print('hello')")

        result = read_file(f, tmp_path)
        assert result is None

    def test_rejects_traversal(self, tmp_path):
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tf:
            Path(tf.name).write_text("outside")
            result = read_file(Path(tf.name), tmp_path)
            assert result is None
            Path(tf.name).unlink()

    def test_rejects_missing_file(self, tmp_path):
        result = read_file(tmp_path / "nope.md", tmp_path)
        assert result is None


class TestBuildHtml:
    def test_returns_html(self):
        html = build_html()
        assert "<!DOCTYPE html>" in html
        assert "marked.min.js" in html
        assert "highlight.min.js" in html

    def test_includes_initial_path(self):
        html = build_html("docs/README.md")
        assert "docs/README.md" in html

    def test_includes_navigate_events_listener(self):
        html = build_html()
        assert "navigate-events" in html


class TestSingleton:
    def test_version_flag(self, capsys):
        import sys
        from unittest.mock import patch
        with patch.object(sys, "argv", ["mdview", "--version"]):
            from tina4_ai.mdview.server import main
            main()
        out = capsys.readouterr().out
        assert "mdview" in out
        assert "0." in out  # version number present

    def test_lock_read_write_remove(self, tmp_path):
        from tina4_ai.mdview import server as s
        original = s.LOCK_FILE
        s.LOCK_FILE = tmp_path / ".mdview.lock"
        try:
            s._write_lock(12345)
            assert s.LOCK_FILE.read_text() == "12345"
            s._remove_lock()
            assert not s.LOCK_FILE.exists()
        finally:
            s.LOCK_FILE = original
