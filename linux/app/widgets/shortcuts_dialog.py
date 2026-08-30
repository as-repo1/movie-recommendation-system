"""linux/app/widgets/shortcuts_dialog.py — Keyboard shortcuts reference modal dialog."""

from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class ShortcutsDialog(Adw.PreferencesWindow):
    """Clean Adwaita keyboard shortcuts cheat-sheet dialog."""

    def __init__(self, parent_window: Gtk.Window) -> None:
        super().__init__()
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_default_size(600, 520)
        self.set_title("RecLens Keyboard Shortcuts")

        page = Adw.PreferencesPage()
        page.set_title("Shortcuts Reference")
        page.set_icon_name("preferences-desktop-keyboard-shortcuts-symbolic")

        # ── Group 1: General Navigation ──────────────────────────────────────
        nav_group = Adw.PreferencesGroup()
        nav_group.set_title("Global & Navigation")
        nav_group.set_description("Access primary sections quickly from anywhere in the app")

        shortcuts = [
            ("Ctrl + K / Ctrl + F", "Instant Spotlight Movie Search", "system-search-symbolic"),
            ("1", "Jump to Home Discovery", "user-home-symbolic"),
            ("2", "Jump to Search & Multi-Filters", "system-search-symbolic"),
            ("3", "Jump to Vibe & Mood Explorer", "starred-symbolic"),
            ("4", "Jump to My Library (Watchlist & Watched)", "view-paged-symbolic"),
            ("?", "Open Keyboard Shortcuts Help", "help-about-symbolic"),
            ("Escape", "Go Back / Close Active Modal", "window-close-symbolic"),
        ]

        for keys, desc, icon in shortcuts:
            row = Adw.ActionRow()
            row.set_title(desc)
            row.set_icon_name(icon)
            
            kbd = Gtk.Label(label=keys)
            kbd.add_css_class("heading")
            kbd.add_css_class("rating-badge")
            row.add_suffix(kbd)
            nav_group.add(row)

        page.add(nav_group)

        # ── Group 2: Movie Detail & Interaction ───────────────────────────────
        movie_group = Adw.PreferencesGroup()
        movie_group.set_title("Movie Player & Detail Actions")
        movie_group.set_description("Actions available on detail pages and carousels")

        movie_shortcuts = [
            ("Space / Enter", "Select / Open Highlighted Movie", "media-playback-start-symbolic"),
            ("T", "Play Official Trailer", "video-x-generic-symbolic"),
            ("W", "Toggle Movie in Watchlist", "bookmark-new-symbolic"),
            ("M", "Mark / Unmark as Watched", "starred-symbolic"),
        ]

        for keys, desc, icon in movie_shortcuts:
            row = Adw.ActionRow()
            row.set_title(desc)
            row.set_icon_name(icon)

            kbd = Gtk.Label(label=keys)
            kbd.add_css_class("heading")
            kbd.add_css_class("rating-badge")
            row.add_suffix(kbd)
            movie_group.add(row)

        page.add(movie_group)
        self.add(page)
