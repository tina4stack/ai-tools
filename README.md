<p align="center">
  <img src="https://tina4.com/logo.svg" alt="Tina4" width="200">
</p>

<h1 align="center">tina4-ai</h1>
<h3 align="center">This Is Now A 4Framework</h3>

<p align="center">
  AI tools for the Tina4 family. Zero third-party dependencies.
</p>

<p align="center">
  <a href="https://pypi.org/project/tina4-ai/"><img src="https://img.shields.io/pypi/v/tina4-ai?color=7b1fa2&label=PyPI" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/python-3.12%2B-blue" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="Zero Deps">
  <img src="https://img.shields.io/badge/license-MIT-7b1fa2" alt="MIT">
  <a href="https://tina4.com"><img src="https://img.shields.io/badge/docs-tina4.com-7b1fa2" alt="Docs"></a>
</p>

<p align="center">
  <a href="#tools">Tools</a> &bull;
  <a href="#install">Install</a> &bull;
  <a href="#mdview">mdview</a> &bull;
  <a href="https://tina4.com">tina4.com</a>
</p>

---

## Tools

| Tool | Description |
|------|-------------|
| **mdview** | Standalone Markdown viewer — renders `.md` files in the browser with full GFM support, live reload, and a file browser sidebar |

---

## Install

The recommended way — installs `mdview` as a standalone CLI tool:

```bash
uv tool install tina4-ai
```

Or with [pipx](https://pipx.pypa.io/):

```bash
pipx install tina4-ai
```

Or into a specific project/virtualenv:

```bash
pip install tina4-ai
```

---

## mdview

A zero-dependency Markdown viewer. Opens any `.md` file in your default browser with full GitHub Flavored Markdown rendering, a file browser sidebar, and live reload on save.

**Features:**
- GFM: tables, task lists, strikethrough, fenced code blocks
- Syntax highlighting for 15+ languages
- File browser sidebar — navigate `.md` files in your project
- Live reload — browser updates automatically when you save
- Dark theme (GitHub Dark Dimmed)
- Zero pip dependencies — stdlib Python + vendored JS

### Usage

```bash
mdview README.md                  # Open a specific file
mdview /path/to/directory         # Browse .md files in a directory
mdview                            # Browse current directory
```

### Quick Start

```bash
uv tool install tina4-ai
mdview README.md
```

Your browser opens automatically. Edit the file and the browser refreshes.

### With Claude Code

When working in Claude Code, ask Claude to open any Markdown file:

```
Show me that plan file
```

Claude runs `mdview /path/to/file.md` and it opens in your browser instantly.

### File Browser

The sidebar lists all `.md` files and directories in your project. Click a directory to expand it, click a file to render it. Hidden directories and common build artefacts (`.git`, `node_modules`, `vendor`, `__pycache__`, `.venv`) are excluded automatically.

### Security

- Binds to `127.0.0.1` only — never exposed on the network
- Path traversal protection — requests outside the project root are rejected
- Only `.md` files are served via the content endpoint

---

## License

MIT (c) 2026 Tina4 Stack
https://opensource.org/licenses/MIT

---

<p align="center"><b>Tina4</b> &mdash; The framework that keeps out of the way of your coding.</p>

---

## Our Sponsors

**Sponsored with 🩵 by Code Infinity**

[<img src="https://codeinfinity.co.za/wp-content/uploads/2025/09/c8e-logo-github.png" alt="Code Infinity" width="100">](https://codeinfinity.co.za/about-open-source-policy?utm_source=github&utm_medium=website&utm_campaign=opensource_campaign&utm_id=opensource)

*Supporting open source communities <span style="color: #1DC7DE;">•</span> Innovate <span style="color: #1DC7DE;">•</span> Code <span style="color: #1DC7DE;">•</span> Empower*
