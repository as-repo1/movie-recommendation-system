#!/usr/bin/env bash
# linux/packaging/build_binary.sh — Build standalone self-contained binary using PyInstaller

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
DIST_DIR="$PROJECT_ROOT/dist"

cd "$PROJECT_ROOT"

echo "🚀 Building self-contained RecLens binary with PyInstaller..."

if [ -f ".venv/bin/pyinstaller" ]; then
    PYINSTALLER=".venv/bin/pyinstaller"
else
    PYINSTALLER="pyinstaller"
fi

"$PYINSTALLER" \
    --name="reclens" \
    --onedir \
    --windowed \
    --noconfirm \
    --clean \
    --add-data="data/processed/movies_clean.parquet:data/processed" \
    --add-data="data/processed/similarity.pkl:data/processed" \
    --add-data="data/processed/movies.pkl:data/processed" \
    --add-data="linux/data/icons:linux/data/icons" \
    --add-data="linux/app/styles/style.css:linux/app/styles" \
    --hidden-import="gi" \
    --hidden-import="gi.repository.Gtk" \
    --hidden-import="gi.repository.Adw" \
    --hidden-import="gi.repository.Gdk" \
    --hidden-import="gi.repository.GLib" \
    --hidden-import="gi.repository.Gio" \
    --hidden-import="pandas" \
    --hidden-import="numpy" \
    --hidden-import="pyarrow" \
    --hidden-import="httpx" \
    linux/app/main.py

echo "✅ Build complete! Standalone application directory: $DIST_DIR/reclens"
