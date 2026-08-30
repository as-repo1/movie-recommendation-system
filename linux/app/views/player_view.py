"""linux/app/views/player_view.py — Embedded WebKitGTK Trailer Player Dialog with Browser Quick-Action."""

from __future__ import annotations

import logging
import urllib.parse
import webbrowser

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

logger = logging.getLogger(__name__)

# Attempt to load WebKit 6.0 or WebKit2 4.1
WEBKIT_AVAILABLE = False
try:
    gi.require_version("WebKit", "6.0")
    from gi.repository import WebKit
    WEBKIT_AVAILABLE = True
except Exception:
    try:
        gi.require_version("WebKit2", "4.1")
        from gi.repository import WebKit2 as WebKit
        WEBKIT_AVAILABLE = True
    except Exception:
        WEBKIT_AVAILABLE = False


class TrailerPlayerDialog(Gtk.Window):
    """In-app modal dialog streaming official movie trailers with direct browser action."""

    def __init__(self, parent_window: Gtk.Window, movie_id: int, movie_title: str) -> None:
        super().__init__()
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_default_size(900, 560)
        self.set_title(f"Trailer — {movie_title}")

        self.movie_id = movie_id
        self.movie_title = movie_title
        self.search_query = f"{movie_title} official trailer"
        self.direct_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(self.search_query)}"

        self._build_ui()

    def _build_ui(self) -> None:
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # ── Header Bar with Open in Browser Button ───────────────────────────
        header = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(
            title=f"Trailer — {self.movie_title}",
            subtitle="Streaming via YouTube / Click External to open directly",
        )
        header.set_title_widget(title_widget)

        # "Open in Browser" Quick Action Button
        browser_btn = Gtk.Button(label="Open in Browser")
        browser_btn.add_css_class("suggested-action")
        browser_btn.set_tooltip_text("Open official trailer in default web browser")
        browser_icon = Gtk.Image.new_from_icon_name("web-browser-symbolic")
        browser_btn.set_icon_name("web-browser-symbolic")
        browser_btn.connect("clicked", lambda _: self._open_external())
        header.pack_end(browser_btn)

        main_box.append(header)

        # ── Embedded Web Player or High-Contrast Fallback ────────────────────
        q_encoded = urllib.parse.quote(self.search_query)
        player_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body, html {{
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    background-color: #11111b;
    color: #cdd6f4;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }}
  .card {{
    text-align: center;
    background: #181825;
    padding: 36px 48px;
    border-radius: 16px;
    border: 1px solid rgba(137, 180, 250, 0.3);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
    max-width: 560px;
  }}
  h2 {{
    margin: 0 0 12px 0;
    color: #89b4fa;
    font-size: 22px;
  }}
  p {{
    color: #a6adc8;
    font-size: 14px;
    line-height: 1.6;
    margin-bottom: 24px;
  }}
  .btn {{
    display: inline-block;
    background: #89b4fa;
    color: #11111b;
    font-weight: 700;
    font-size: 15px;
    padding: 12px 28px;
    border-radius: 999px;
    text-decoration: none;
    transition: transform 0.15s, background 0.15s;
  }}
  .btn:hover {{
    background: #b4befe;
    transform: scale(1.04);
  }}
  iframe {{
    width: 100%;
    height: 100%;
    border: none;
  }}
</style>
</head>
<body>
  <iframe src="https://www.youtube.com/embed?listType=search&list={q_encoded}&autoplay=1" allow="autoplay; encrypted-media; fullscreen" allowfullscreen></iframe>
</body>
</html>"""

        if WEBKIT_AVAILABLE:
            try:
                web_view = WebKit.WebView()
                web_view.set_vexpand(True)
                web_view.set_hexpand(True)
                # Load with base_uri="https://www.youtube.com" to avoid origin restriction errors
                web_view.load_html(player_html, base_uri="https://www.youtube.com")
                main_box.append(web_view)
                self.set_child(main_box)
                return
            except Exception as e:
                logger.warning("Failed to initialize WebKit view: %s", e)

        # Fallback UI if WebKit is unavailable
        fallback_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        fallback_box.set_valign(Gtk.Align.CENTER)
        fallback_box.set_halign(Gtk.Align.CENTER)
        fallback_box.set_vexpand(True)

        icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
        icon.set_pixel_size(64)
        icon.add_css_class("accent")
        fallback_box.append(icon)

        lbl = Gtk.Label(label=f"Watch '{self.movie_title}' Official Trailer")
        lbl.add_css_class("title-2")
        fallback_box.append(lbl)

        open_btn = Gtk.Button(label="Open Official Trailer in Browser")
        open_btn.add_css_class("suggested-action")
        open_btn.add_css_class("pill")
        open_btn.connect("clicked", lambda _: self._open_external())
        fallback_box.append(open_btn)

        main_box.append(fallback_box)
        self.set_child(main_box)

    def _open_external(self) -> None:
        webbrowser.open(self.direct_url)
