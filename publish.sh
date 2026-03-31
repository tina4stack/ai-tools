#!/bin/bash
# Publish tina4-ai to PyPI
# Usage: ./publish.sh [test]
#   ./publish.sh        -> publish to PyPI
#   ./publish.sh test   -> publish to TestPyPI

set -e

echo "=== tina4-ai — Build & Publish ==="
echo ""

# Clean previous builds
rm -rf dist/ build/ *.egg-info tina4_ai.egg-info/

# Run tests first
echo "Running tests..."
.venv/bin/python -m pytest tests/ -q
echo ""

# Build
echo "Building package..."
.venv/bin/python -m build
echo ""

# Show what was built
echo "Built:"
ls -lh dist/
echo ""

# Publish
if [ "$1" = "test" ]; then
    echo "Publishing to TestPyPI..."
    .venv/bin/python -m twine upload --repository testpypi dist/*
    echo ""
    echo "Install from TestPyPI:"
    echo "  pip install --index-url https://test.pypi.org/simple/ tina4-ai"
else
    echo "Publishing to PyPI..."
    .venv/bin/python -m twine upload dist/*
    echo ""
    echo "Install:"
    echo "  pip install tina4-ai"
fi

echo ""
echo "Done!"
