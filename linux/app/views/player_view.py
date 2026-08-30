"""linux/app/views/player_view.py — Embedded WebKitGTK Trailer Player Dialog."""

from __future__ import annotations

import logging
import urllib.parse

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
    """In-app modal dialog streaming official movie trailers via WebKitGTK."""

    def __init__(self, parent_window: Gtk.Window, movie_id: int, movie_title: str) -> None:
        super().__init__()
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_default_size(880, 540)
        self.set_title(f"Trailer — {movie_title}")

        self.movie_id = movie_id
        self.movie_title = movie_title

        self._build_ui()

    def _build_ui(self) -> None:
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Header Bar
        header = Gtk.HeaderBar()
        title_widget = Adw.WindowTitle(title=f"Trailer — {self.movie_title}", subtitle="Streaming via YouTube") if hasattr(Adw, "WindowTitle") else Gtk.Label(label=f"Trailer — {self.movie_title}")
        header.set_title_widget(title_widget)
        main_box.append(header)

        # Query YouTube Embed for movie trailer
        q = urllib.parse.quote_plus(f"{self.movie_title} official trailer")
        embed_url = f"https://www.youtube.com/embed?listType=search&list={q}&autoplay=1"

        if WEBKIT_AVAILABLE:
            try:
                web_view = WebKit.WebView()
                web_view.set_vexpand(True)
                web_view.set_hexpand(True)
                web_view.load_uri(embed_url)
                main_box.append(web_view)
                self.set_child(main_box)
                return
            except Exception as e:
                logger.warning("Failed to initialize WebKit view: %s", e)

        # Fallback if WebKit is unavailable or fails
        fallback_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        fallback_box.set_valign(Gtk.Align.CENTER)
        fallback_box.set_halign(Gtk.Align.CENTER)
        fallback_box.set_margin_top(48)
        fallback_box.set_margin_bottom(48)

        icon = Gtk.Image.new_from_icon_name("media-playback-start-symbolic")
        icon.set_pixel_size(64)
        icon.add_css_class("accent")
        fallback_box.append(icon)

        lbl = Gtk.Label(label=f"Watch '{self.movie_title}' Official Trailer")
        lbl.add_css_class("title-2")
        fallback_box.append(lbl)

        open_btn = Gtk.Button(label="Open in Default Browser")
        open_btn.add_css_class("suggested-action")
        open_btn.add_css_class("pill")
        direct_url = f"https://www.youtube.com/results?search_query={q}"
        open_btn.connect("clicked", lambda _: self._open_external(direct_url))
        fallback_box.append(open_btn)

        main_box.append(fallback_box)
        self.set_child(main_box)

    def _open_external(self, url: str) -> None:
        import webbrowser
        webbrowser.open(url)
        self.close()
