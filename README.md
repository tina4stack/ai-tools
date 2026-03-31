# tina4-ai

AI tools for the Tina4 family.

## Tools

### mdview

A standalone Markdown viewer that renders `.md` files in the browser with full GitHub Flavored Markdown support.

**Features:**
- GFM rendering: tables, task lists, strikethrough, fenced code blocks
- Syntax highlighting for 15+ languages
- File browser sidebar to navigate `.md` files
- Live reload on file changes
- Dark theme (GitHub Dark Dimmed)
- Zero external dependencies

**Install:**

```bash
pip install tina4-ai
```

**Usage:**

```bash
mdview README.md              # Open a specific file
mdview /path/to/directory     # Browse .md files in a directory
mdview                        # Browse current directory
```

## License

MIT
