#!/usr/bin/env bash
# linux/packaging/build_appimage.sh — AppImage build recipe for RecLens

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
APPDIR="/tmp/reclens.AppDir"

echo "📦 Preparing RecLens AppDir at $APPDIR..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin" "$APPDIR/usr/lib" "$APPDIR/usr/share/applications" "$APPDIR/usr/share/icons/hicolor/scalable/apps"

# Copy App Files
cp "$PROJECT_ROOT/linux/data/org.reclens.RecLens.desktop" "$APPDIR/org.reclens.RecLens.desktop"
cp "$PROJECT_ROOT/linux/data/org.reclens.RecLens.desktop" "$APPDIR/usr/share/applications/"
cp "$PROJECT_ROOT/linux/data/icons/org.reclens.RecLens.svg" "$APPDIR/org.reclens.RecLens.svg"
cp "$PROJECT_ROOT/linux/data/icons/org.reclens.RecLens.svg" "$APPDIR/usr/share/icons/hicolor/scalable/apps/"

# Create AppRun entrypoint
cat << 'EOF' > "$APPDIR/AppRun"
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
export PYTHONPATH="${HERE}/usr/share/reclens:${PYTHONPATH}"

exec python3 "${HERE}/usr/share/reclens/linux/app/main.py" "$@"
EOF
chmod +x "$APPDIR/AppRun"

echo "ℹ️ AppDir prepared. Run 'appimagetool $APPDIR RecLens-2.1.0-x86_64.AppImage' to produce the standalone binary."
