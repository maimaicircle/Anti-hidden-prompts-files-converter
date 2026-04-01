#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Checking Python 3 ==="
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 was not found. Please install Python 3 first."
    exit 1
fi

echo "=== Checking requirements.txt ==="
if [ ! -f "requirements.txt" ]; then
    echo "requirements.txt was not found in: $SCRIPT_DIR"
    exit 1
fi

echo "=== Installing dependencies ==="
python3 -m pip install -r requirements.txt

echo "=== Running program ==="
python3 pdf_png_rebuild_gui.py
