#!/usr/bin/env bash
# scripts/build_release.sh — Comprehensive Multi-Target Release Builder
# Generates all production artifacts and binaries into the 'built-things/' directory.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
OUT_DIR="$PROJECT_ROOT/built-things"
VERSION="2.1.0"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

cd "$PROJECT_ROOT"

echo "============================================================"
echo "🚀 Building RecLens Production Release v${VERSION}"
echo "📁 Output Directory: ${OUT_DIR}"
echo "============================================================"

# 1. Clean / Initialize output directory
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

# 2. Run Automated Verification Tests
echo ""
echo "🧪 [1/5] Running test suite validation..."
if [ -f ".venv/bin/pytest" ]; then
    .venv/bin/pytest tests/test_linux_app.py -q || { echo "❌ Tests failed!"; exit 1; }
    echo "✅ Test suite passed successfully."
else
    echo "⚠️ .venv/bin/pytest not found, skipping unit test check."
fi

# 3. Build Web Frontend (React + Vite)
echo ""
echo "🌐 [2/5] Building Web Frontend Production Bundle..."
if [ -d "frontend" ] && command -v npm >/dev/null 2>&1; then
    cd frontend
    npm run build
    cd "$PROJECT_ROOT"
    mkdir -p "$OUT_DIR/web-dist"
    cp -r frontend/dist/* "$OUT_DIR/web-dist/"
    tar -czf "$OUT_DIR/reclens-web-v${VERSION}.tar.gz" -C "$OUT_DIR" web-dist
    echo "✅ Web bundle generated: $OUT_DIR/reclens-web-v${VERSION}.tar.gz"
else
    echo "⚠️ Skipping frontend build (npm or frontend dir not found)."
fi

# 4. Build Standalone Linux Desktop Binary with PyInstaller
echo ""
echo "🐧 [3/5] Building Standalone Linux Desktop Binary..."
if [ -f ".venv/bin/pyinstaller" ]; then
    PYINSTALLER=".venv/bin/pyinstaller"
elif command -v pyinstaller >/dev/null 2>&1; then
    PYINSTALLER="pyinstaller"
else
    echo "Installing PyInstaller..."
    uv pip install pyinstaller
    PYINSTALLER=".venv/bin/pyinstaller"
fi

BUILD_TEMP="$PROJECT_ROOT/build_temp"
rm -rf "$BUILD_TEMP" "$PROJECT_ROOT/dist/reclens"

"$PYINSTALLER" \
    --name="reclens" \
    --onedir \
    --windowed \
    --noconfirm \
    --clean \
    --paths="." \
    --collect-all="linux" \
    --collect-all="src" \
    --workpath="$BUILD_TEMP" \
    --distpath="$OUT_DIR" \
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


rm -rf "$BUILD_TEMP" "$PROJECT_ROOT/reclens.spec"

# Package desktop release directory
DESKTOP_DIR="$OUT_DIR/reclens-linux-x86_64"
rm -rf "$DESKTOP_DIR"
mv "$OUT_DIR/reclens" "$DESKTOP_DIR"

# Add desktop file and launch helper
cat << 'EOF' > "$DESKTOP_DIR/launch.sh"
#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export LD_LIBRARY_PATH="$SCRIPT_DIR:$LD_LIBRARY_PATH"
exec "$SCRIPT_DIR/reclens" "$@"
EOF
chmod +x "$DESKTOP_DIR/launch.sh"

tar -czf "$OUT_DIR/reclens-linux-x86_64-v${VERSION}.tar.gz" -C "$OUT_DIR" reclens-linux-x86_64
echo "✅ Linux Desktop release generated: $OUT_DIR/reclens-linux-x86_64-v${VERSION}.tar.gz"

# 5. Build Backend & API Bundle
echo ""
echo "⚙️ [4/5] Packaging FastAPI Backend & CLI Bundle..."
BACKEND_TEMP="$OUT_DIR/backend-bundle"
mkdir -p "$BACKEND_TEMP"
cp -r backend "$BACKEND_TEMP/"
cp -r data/processed "$BACKEND_TEMP/data"
cp pyproject.toml requirements.txt "$BACKEND_TEMP/" 2>/dev/null || true
tar -czf "$OUT_DIR/reclens-backend-v${VERSION}.tar.gz" -C "$OUT_DIR" backend-bundle
rm -rf "$BACKEND_TEMP"
echo "✅ Backend bundle generated: $OUT_DIR/reclens-backend-v${VERSION}.tar.gz"

# 6. Generate Checksums and Release Notes
echo ""
echo "📝 [5/5] Generating SHA256 Checksums and Release Metadata..."
cd "$OUT_DIR"
sha256sum *.tar.gz > SHA256SUMS.txt 2>/dev/null || true

cat << EOF > RELEASE_NOTES.md
# RecLens Release v${VERSION} (${TIMESTAMP})

## 📦 Release Artifacts in \`built-things/\`

| Artifact File | Target Platform | Description |
| :--- | :--- | :--- |
| \`reclens-linux-x86_64-v${VERSION}.tar.gz\` | Linux x86_64 Desktop | Standalone GTK4/Libadwaita application bundle |
| \`reclens-web-v${VERSION}.tar.gz\` | Web Browsers | Production optimized React + Vite static bundle |
| \`reclens-backend-v${VERSION}.tar.gz\` | Server / Cloud / Docker | FastAPI Recommendation API & Microservices |
| \`SHA256SUMS.txt\` | All | Cryptographic integrity verification checksums |

## 🌟 Key Features in v${VERSION}
- 🎨 **6 Dynamic Color Themes**: Catppuccin Mocha, Nord Frost, Dracula Pro, OLED Black, Sunset Amber, Adwaita Clean Light.
- 💬 **In-Process AI Movie Chat Companion**: Instant Q&A, trivia, director styles, and box office stats.
- 🍿 **AI Mood Marathon Builder**: Paced 5-movie themed playlists.
- 🌐 **External Reference Database Links**: Direct IMDb, TMDB, Wikipedia, and Letterboxd buttons.
- 🔍 **Advanced Search Syntax**: \`director:nolan >2010\`, \`actor:dicaprio\`, \`genre:scifi rating:>8\`.
- 💾 **Export & Save**: Watchlist JSON/Markdown export and poster downloading.

## 🚀 Quick Launch
\`\`\`bash
# Extract and launch standalone Linux Desktop app
tar -xzf reclens-linux-x86_64-v${VERSION}.tar.gz
cd reclens-linux-x86_64
./launch.sh
\`\`\`
EOF

echo ""
echo "============================================================"
echo "🎉 Release build finished successfully! Contents of built-things/:"
echo "============================================================"
ls -lh "$OUT_DIR"
