"""linux/app/views/watchlist_view.py — User Watchlist and Watched History manager."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk
from linux.app.db import local_db
from linux.app.widgets.movie_card import MovieCard


class WatchlistView(Gtk.ScrolledWindow):
    """User Watchlist & History view with export/import tools."""

    def __init__(self, on_movie_selected: Callable[[int], None], on_explore: Callable[[], None]) -> None:
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.on_movie_selected = on_movie_selected
        self.on_explore = on_explore
        self.active_tab: str = "watchlist"

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_box.set_margin_start(24)
        self.main_box.set_margin_end(24)
        self.main_box.set_margin_top(16)
        self.main_box.set_margin_bottom(32)

        self._build_ui()
        self.set_child(self.main_box)
        self.refresh()

    def _build_ui(self) -> None:
        # ── Header & Action Buttons ──────────────────────────────────────────
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        title_lbl = Gtk.Label(label="📌 My Movie Library")
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.add_css_class("title-2")
        header_box.append(title_lbl)

        # Tab Switcher
        tabs_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        tabs_box.set_hexpand(True)
        tabs_box.set_halign(Gtk.Align.END)

        self.btn_wl = Gtk.Button(label="Watchlist")
        self.btn_wl.add_css_class("pill")
        self.btn_wl.add_css_class("suggested-action")
        self.btn_wl.connect("clicked", lambda _: self._set_tab("watchlist"))
        tabs_box.append(self.btn_wl)

        self.btn_watched = Gtk.Button(label="Watched History")
        self.btn_watched.add_css_class("pill")
        self.btn_watched.connect("clicked", lambda _: self._set_tab("watched"))
        tabs_box.append(self.btn_watched)

        # Export Button
        export_btn = Gtk.Button(label="Export")
        export_btn.add_css_class("flat")
        export_btn.connect("clicked", self._on_export_clicked)
        tabs_box.append(export_btn)

        header_box.append(tabs_box)
        self.main_box.append(header_box)

        # ── Grid of Saved Movies ─────────────────────────────────────────────
        self.grid = Gtk.FlowBox()
        self.grid.set_valign(Gtk.Align.START)
        self.grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.grid.set_column_spacing(16)
        self.grid.set_row_spacing(20)
        self.grid.set_min_children_per_line(2)
        self.grid.set_max_children_per_line(8)
        self.main_box.append(self.grid)

    def _set_tab(self, tab: str) -> None:
        self.active_tab = tab
        if tab == "watchlist":
            self.btn_wl.add_css_class("suggested-action")
            self.btn_watched.remove_css_class("suggested-action")
        else:
            self.btn_watched.add_css_class("suggested-action")
            self.btn_wl.remove_css_class("suggested-action")
        self.refresh()

    def refresh(self) -> None:
        while child := self.grid.get_first_child():
            self.grid.remove(child)

        if self.active_tab == "watchlist":
            items = local_db.get_watchlist()
            empty_title = "Your Watchlist is Empty"
            empty_desc = "Explore movies and click '+ Add to Watchlist' to save them for later."
        else:
            items = local_db.get_watched()
            empty_title = "No Watched Movies Yet"
            empty_desc = "Mark films as watched from movie detail pages to build your personal history."

        if not items:
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            empty_box.set_margin_top(64)
            empty_box.set_halign(Gtk.Align.CENTER)

            icon = Gtk.Image.new_from_icon_name("starred-symbolic")
            icon.set_pixel_size(48)
            icon.add_css_class("dim-label")
            empty_box.append(icon)

            lbl_t = Gtk.Label(label=empty_title)
            lbl_t.add_css_class("title-3")
            empty_box.append(lbl_t)

            lbl_d = Gtk.Label(label=empty_desc)
            lbl_d.add_css_class("dim-label")
            empty_box.append(lbl_d)

            explore_btn = Gtk.Button(label="Explore Catalog")
            explore_btn.add_css_class("suggested-action")
            explore_btn.add_css_class("pill")
            explore_btn.set_margin_top(8)
            explore_btn.connect("clicked", lambda _: self.on_explore())
            empty_box.append(explore_btn)

            self.grid.append(empty_box)
            return

        for item in items:
            m_dict = {
                "movie_id": item.movie_id,
                "title": item.title,
                "year": item.year,
                "poster_path": item.poster_path,
                "vote_average": item.vote_average,
            }
            card = MovieCard(m_dict, on_selected=self.on_movie_selected, width=155, height=230)
            self.grid.append(card)

    def _on_export_clicked(self, btn: Gtk.Button) -> None:
        export_file = Path.home() / "Downloads" / "reclens_library_export.json"
        export_file.parent.mkdir(parents=True, exist_ok=True)
        if local_db.export_data(export_file, format="json"):
            # Show toast / alert
            btn.set_label("✓ Exported to Downloads!")
            btn.add_css_class("accent")
