"""linux/app/widgets/spotlight_search.py — Instant Ctrl+K Spotlight Search overlay dialog."""

from __future__ import annotations

from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gdk, GLib, Gtk
from linux.app.engine import engine
from linux.app.image_loader import image_loader


class SpotlightSearchDialog(Gtk.Window):
    """Global Ctrl+K Spotlight Search dialog for lightning-fast fuzzy catalog search."""

    def __init__(self, parent_window: Gtk.Window, on_movie_selected: Callable[[int], None]) -> None:
        super().__init__()
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_default_size(620, 480)
        self.set_title("Search RecLens")
        self.add_css_class("spotlight-window")

        self.on_movie_selected = on_movie_selected
        self._current_results: list[dict[str, Any]] = []
        self._search_debounce_id: int = 0

        self._build_ui()
        self._setup_key_controller()

    def _build_ui(self) -> None:
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # ── Search Entry Header ──────────────────────────────────────────────
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        entry_box.set_margin_start(16)
        entry_box.set_margin_end(16)
        entry_box.set_margin_top(12)
        entry_box.set_margin_bottom(12)

        search_icon = Gtk.Image.new_from_icon_name("system-search-symbolic")
        search_icon.set_pixel_size(20)
        search_icon.add_css_class("accent")
        entry_box.append(search_icon)

        self.entry = Gtk.SearchEntry()
        self.entry.set_placeholder_text("Search across 15,000+ movies by title, director, or cast...")
        self.entry.set_hexpand(True)
        self.entry.add_css_class("spotlight-entry")
        self.entry.connect("search-changed", self._on_search_changed)
        self.entry.connect("activate", self._on_entry_activate)
        entry_box.append(self.entry)

        shortcut_label = Gtk.Label(label="ESC to close")
        shortcut_label.add_css_class("dim-label")
        shortcut_label.add_css_class("caption")
        entry_box.append(shortcut_label)

        main_box.append(entry_box)

        # Separator
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # ── Results List ─────────────────────────────────────────────────────
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.add_css_class("navigation-sidebar")
        self.list_box.connect("row-activated", self._on_row_activated)
        scrolled.set_child(self.list_box)

        main_box.append(scrolled)
        self.set_child(main_box)

    def _setup_key_controller(self) -> None:
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

    def _on_key_pressed(self, controller, keyval, keycode, state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        elif keyval == Gdk.KEY_Down:
            row = self.list_box.get_selected_row()
            if row:
                next_row = self.list_box.get_row_at_index(row.get_index() + 1)
                if next_row:
                    self.list_box.select_row(next_row)
            else:
                first_row = self.list_box.get_row_at_index(0)
                if first_row:
                    self.list_box.select_row(first_row)
            return True
        elif keyval == Gdk.KEY_Up:
            row = self.list_box.get_selected_row()
            if row and row.get_index() > 0:
                prev_row = self.list_box.get_row_at_index(row.get_index() - 1)
                if prev_row:
                    self.list_box.select_row(prev_row)
            return True
        return False

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        if self._search_debounce_id:
            GLib.source_remove(self._search_debounce_id)
        self._search_debounce_id = GLib.timeout_add(150, self._do_search)

    def _do_search(self) -> bool:
        query = self.entry.get_text().strip()
        if not query:
            self._render_results([])
            return False

        results = engine.search(query=query, limit=12)
        self._render_results(results)
        return False

    def _render_results(self, results: list[dict[str, Any]]) -> None:
        self._current_results = results

        # Clear existing rows
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)

        if not results:
            if self.entry.get_text().strip():
                empty_row = Gtk.ListBoxRow()
                lbl = Gtk.Label(label="No matching movies found.")
                lbl.set_margin_top(24)
                lbl.set_margin_bottom(24)
                lbl.add_css_class("dim-label")
                empty_row.set_child(lbl)
                self.list_box.append(empty_row)
            return

        for idx, movie in enumerate(results):
            row = Gtk.ListBoxRow()
            row.movie_id = movie["movie_id"]

            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row_box.set_margin_top(8)
            row_box.set_margin_bottom(8)
            row_box.set_margin_start(16)
            row_box.set_margin_end(16)

            # Tiny thumbnail
            picture = Gtk.Picture()
            picture.set_size_request(36, 52)
            picture.set_content_fit(Gtk.ContentFit.COVER)
            picture.add_css_class("movie-poster-frame")
            row_box.append(picture)

            poster_path = movie.get("poster_path", "")
            if poster_path:
                image_loader.get_texture_async(poster_path, callback=lambda tex, pic=picture: tex and pic.set_paintable(tex))

            # Info box
            info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            info_box.set_hexpand(True)

            title_lbl = Gtk.Label(label=movie["title"])
            title_lbl.set_halign(Gtk.Align.START)
            title_lbl.add_css_class("heading")
            info_box.append(title_lbl)

            year = movie.get("year")
            genres = ", ".join(movie.get("genres", [])[:2])
            director = movie.get("director", "")
            meta_str = f"{year or ''} · {genres}" if not director else f"{year or ''} · {genres} · Dir: {director}"
            meta_lbl = Gtk.Label(label=meta_str)
            meta_lbl.set_halign(Gtk.Align.START)
            meta_lbl.add_css_class("dim-label")
            meta_lbl.add_css_class("caption")
            info_box.append(meta_lbl)

            row_box.append(info_box)

            # Rating / Match Pill
            rating_lbl = Gtk.Label(label=f"★ {movie.get('vote_average', 0.0):.1f}")
            rating_lbl.add_css_class("rating-badge")
            rating_lbl.set_valign(Gtk.Align.CENTER)
            row_box.append(rating_lbl)

            row.set_child(row_box)
            self.list_box.append(row)

        # Select first row by default
        if first := self.list_box.get_row_at_index(0):
            self.list_box.select_row(first)

    def _on_entry_activate(self, entry: Gtk.SearchEntry) -> None:
        selected_row = self.list_box.get_selected_row()
        if selected_row and hasattr(selected_row, "movie_id"):
            self._select_movie(selected_row.movie_id)

    def _on_row_activated(self, list_box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        if hasattr(row, "movie_id"):
            self._select_movie(row.movie_id)

    def _select_movie(self, movie_id: int) -> None:
        self.close()
        self.on_movie_selected(movie_id)
