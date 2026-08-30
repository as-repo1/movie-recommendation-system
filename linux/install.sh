#!/usr/bin/env bash
# linux/install.sh — Install RecLens Native Linux Application to ~/.local/

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "📦 Installing RecLens Native Linux Desktop Application..."

# 1. Create target directories
BIN_DIR="$HOME/.local/bin"
APP_DIR="$HOME/.local/share/applications"
ICON_SCALABLE="$HOME/.local/share/icons/hicolor/scalable/apps"
ICON_512="$HOME/.local/share/icons/hicolor/512x512/apps"
META_DIR="$HOME/.local/share/metainfo"

mkdir -p "$BIN_DIR" "$APP_DIR" "$ICON_SCALABLE" "$ICON_512" "$META_DIR"

# 2. Install launcher binary wrapper
cat << 'EOF' > "$BIN_DIR/reclens"
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${RECLENS_HOME:-PROJECT_ROOT_PLACEHOLDER}"

if [ -f "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON_EXEC="$PROJECT_DIR/.venv/bin/python"
else
    PYTHON_EXEC="python3"
fi

export PYTHONPATH="$PROJECT_DIR:$PYTHONPATH"
exec "$PYTHON_EXEC" "$PROJECT_DIR/linux/app/main.py" "$@"
EOF

# Substitute actual project directory path
sed -i "s|PROJECT_ROOT_PLACEHOLDER|$PROJECT_ROOT|g" "$BIN_DIR/reclens"
chmod +x "$BIN_DIR/reclens"

# 3. Install Icons
cp "$SCRIPT_DIR/data/icons/org.reclens.RecLens.svg" "$ICON_SCALABLE/org.reclens.RecLens.svg"
if [ -f "$SCRIPT_DIR/data/icons/512x512/org.reclens.RecLens.png" ]; then
    cp "$SCRIPT_DIR/data/icons/512x512/org.reclens.RecLens.png" "$ICON_512/org.reclens.RecLens.png"
fi

# 4. Install Desktop Entry
cp "$SCRIPT_DIR/data/org.reclens.RecLens.desktop" "$APP_DIR/org.reclens.RecLens.desktop"
sed -i "s|Exec=reclens|Exec=$BIN_DIR/reclens|g" "$APP_DIR/org.reclens.RecLens.desktop"

# 5. Install AppStream Metadata
cp "$SCRIPT_DIR/data/org.reclens.RecLens.metainfo.xml" "$META_DIR/org.reclens.RecLens.metainfo.xml"

# 6. Update desktop & icon caches if tools exist
if command -v update-desktop-database > /dev/null 2>&1; then
    update-desktop-database "$APP_DIR" || true
fi

if command -v gtk-update-icon-cache > /dev/null 2>&1; then
    gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" > /dev/null 2>&1 || true
fi

echo "✅ RecLens successfully installed!"
echo "   • Binary launcher: $BIN_DIR/reclens"
echo "   • Desktop Entry:   $APP_DIR/org.reclens.RecLens.desktop"
echo "   • Application will now appear in your GNOME/KDE App Launcher."
