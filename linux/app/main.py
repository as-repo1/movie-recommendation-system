"""linux/app/main.py — RecLens Linux Application entrypoint and CLI dispatcher."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk

# Ensure root workspace is on python path
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    PROJECT_ROOT = Path(sys._MEIPASS)
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from linux.app.db import local_db
from linux.app.engine import engine
from linux.app.window import RecLensWindow

APP_ID = "org.reclens.RecLens"
VERSION = "2.1.0"


class RecLensApplication(Adw.Application):
    """Main Adw.Application instance for RecLens Linux."""

    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.window: RecLensWindow | None = None

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)

        # ── Load In-Process ML Engine ─────────────────────────────────────────
        engine.load()

        # ── Load CSS Stylesheet ───────────────────────────────────────────────
        self._load_css()

        # ── Register Custom Icon Directory ───────────────────────────────────
        icon_dir = Path(__file__).parent.parent / "data" / "icons"
        if icon_dir.exists():
            display = Gdk.Display.get_default()
            if display:
                icon_theme = Gtk.IconTheme.get_for_display(display)
                icon_theme.add_search_path(str(icon_dir))

    def _load_css(self) -> None:
        css_path = Path(__file__).parent / "styles" / "style.css"
        if css_path.exists():
            css_provider = Gtk.CssProvider()
            try:
                css_provider.load_from_path(str(css_path))
                display = Gdk.Display.get_default()
                if display:
                    Gtk.StyleContext.add_provider_for_display(
                        display,
                        css_provider,
                        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
                    )
            except Exception as e:
                print(f"Warning: Failed to load CSS styles: {e}", file=sys.stderr)

    def do_activate(self) -> None:
        if not self.window:
            self.window = RecLensWindow(self)
        self.window.present()

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        args = command_line.get_arguments()
        
        # CLI Argument Dispatcher
        if len(args) > 1:
            cmd = args[1].lower()

            if cmd in ["-v", "--version"]:
                print(f"RecLens Desktop v{VERSION}")
                return 0

            elif cmd in ["search", "-s"]:
                if len(args) > 2:
                    q = " ".join(args[2:])
                    engine.load()
                    results = engine.search(query=q, limit=10)
                    print(f"\n🎬 RecLens Search Results for '{q}':\n" + "=" * 60)
                    if not results:
                        print("  No matching movies found.")
                    for r in results:
                        year = f"({r['year']})" if r.get('year') else ""
                        genres = ", ".join(r.get('genres', [])[:2])
                        print(f"  • {r['title']} {year} | Rating: ★ {r.get('vote_average', 0):.1f} | {genres}")
                    print("=" * 60 + "\n")
                    return 0
                else:
                    print("Usage: reclens search <movie title or keyword>")
                    return 1

            elif cmd in ["recommend", "rec", "-r"]:
                if len(args) > 2:
                    target = " ".join(args[2:])
                    engine.load()
                    recs = engine.get_similar(target, n=8)
                    print(f"\n🎯 Recommendations for '{target}':\n" + "=" * 65)
                    if not recs:
                        print(f"  No recommendations found for '{target}'.")
                    for r in recs:
                        year = f"({r['year']})" if r.get('year') else ""
                        match = f"{r.get('match_percentage', 0)}% Match"
                        reason = f" · Reason: {r.get('match_reason', '')}" if r.get('match_reason') else ""
                        print(f"  • {r['title']} {year} | {match}{reason}")
                    print("=" * 65 + "\n")
                    return 0
                else:
                    print("Usage: reclens recommend <movie title>")
                    return 1

            elif cmd in ["watchlist", "wl"]:
                items = local_db.get_watchlist()
                print("\n📌 Your Saved Watchlist:\n" + "=" * 50)
                if not items:
                    print("  Your watchlist is currently empty.")
                for item in items:
                    print(f"  • {item.title} ({item.year or 'N/A'}) — Added: {item.added_at[:10]}")
                print("=" * 50 + "\n")
                return 0

        self.activate()
        return 0


def main() -> int:
    app = RecLensApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
