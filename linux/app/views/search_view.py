"""linux/app/views/search_view.py — Instant search & multi-filtered discovery canvas."""

from __future__ import annotations

from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GLib, Gtk
from linux.app.engine import engine
from linux.app.widgets.movie_card import MovieCard


class SearchView(Gtk.ScrolledWindow):
    """Search and filter view with real-time text query and multi-parameter filters."""

    def __init__(self, on_movie_selected: Callable[[int], None]) -> None:
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.on_movie_selected = on_movie_selected
        self._debounce_timer: int = 0

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
        self.main_box.set_vexpand(True)
        self.main_box.set_hexpand(True)
        self.main_box.set_margin_start(24)
        self.main_box.set_margin_end(24)
        self.main_box.set_margin_top(16)
        self.main_box.set_margin_bottom(32)


        self._build_ui()
        self.set_child(self.main_box)

        # Trigger initial default search
        self._execute_search()

    def _build_ui(self) -> None:
        # ── Header & Title ───────────────────────────────────────────────────
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        title_lbl = Gtk.Label(label="🔍 Search & Filter Catalog")
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.add_css_class("title-2")
        header_box.append(title_lbl)

        self.count_lbl = Gtk.Label(label="")
        self.count_lbl.add_css_class("dim-label")
        self.count_lbl.set_valign(Gtk.Align.CENTER)
        header_box.append(self.count_lbl)

        self.main_box.append(header_box)

        # ── Search Input ─────────────────────────────────────────────────────
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Type movie title, director, or actor name...")
        self.search_entry.add_css_class("spotlight-entry")
        self.search_entry.connect("search-changed", self._on_input_changed)
        self.main_box.append(self.search_entry)

        # ── Filter Controls Bar ──────────────────────────────────────────────
        filter_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        filter_box.set_hexpand(True)

        # 1. Genre DropDown
        genres = ["All Genres"] + engine.get_all_genres()
        genre_list = Gtk.StringList.new(genres)
        self.genre_drop = Gtk.DropDown.new(genre_list, None)
        self.genre_drop.set_selected(0)
        self.genre_drop.connect("notify::selected", self._on_filter_changed)
        filter_box.append(self.genre_drop)

        # 2. Decade DropDown
        decades = ["All Decades"] + [f"{d}s" for d in engine.get_all_decades()]
        decade_list = Gtk.StringList.new(decades)
        self.decade_drop = Gtk.DropDown.new(decade_list, None)
        self.decade_drop.set_selected(0)
        self.decade_drop.connect("notify::selected", self._on_filter_changed)
        filter_box.append(self.decade_drop)

        # 3. Runtime Category DropDown
        runtimes = ["All Runtimes", "Short (<45m)", "Feature (45-150m)", "Epic (>150m)"]
        runtime_list = Gtk.StringList.new(runtimes)
        self.runtime_drop = Gtk.DropDown.new(runtime_list, None)
        self.runtime_drop.set_selected(0)
        self.runtime_drop.connect("notify::selected", self._on_filter_changed)
        filter_box.append(self.runtime_drop)

        # 4. Sort Order
        sorts = ["Most Popular", "Highest Rated", "Newest First", "Highest Profit"]
        sort_list = Gtk.StringList.new(sorts)
        self.sort_drop = Gtk.DropDown.new(sort_list, None)
        self.sort_drop.set_selected(0)
        self.sort_drop.connect("notify::selected", self._on_filter_changed)
        filter_box.append(self.sort_drop)

        self.main_box.append(filter_box)

        # ── Movie Grid FlowBox ───────────────────────────────────────────────
        self.grid = Gtk.FlowBox()
        self.grid.set_valign(Gtk.Align.START)
        self.grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.grid.set_column_spacing(16)
        self.grid.set_row_spacing(20)
        self.grid.set_min_children_per_line(2)
        self.grid.set_max_children_per_line(8)
        self.main_box.append(self.grid)

    def _on_input_changed(self, entry: Gtk.SearchEntry) -> None:
        if self._debounce_timer:
            GLib.source_remove(self._debounce_timer)
        self._debounce_timer = GLib.timeout_add(150, self._execute_search)

    def _on_filter_changed(self, dropdown, param) -> None:
        self._execute_search()

    def _execute_search(self) -> bool:
        query = self.search_entry.get_text().strip()

        # Genre
        selected_genre_idx = self.genre_drop.get_selected()
        genre_item = self.genre_drop.get_model().get_string(selected_genre_idx)
        genre = "All" if genre_item == "All Genres" else genre_item

        # Decade
        selected_decade_idx = self.decade_drop.get_selected()
        decade_str = self.decade_drop.get_model().get_string(selected_decade_idx)
        decade = int(decade_str.rstrip("s")) if decade_str != "All Decades" else None

        # Runtime
        selected_rt_idx = self.runtime_drop.get_selected()
        rt_str = self.runtime_drop.get_model().get_string(selected_rt_idx)
        if "Short" in rt_str:
            runtime_cat = "Short"
        elif "Feature" in rt_str:
            runtime_cat = "Feature"
        elif "Epic" in rt_str:
            runtime_cat = "Epic"
        else:
            runtime_cat = "All"

        # Sort
        selected_sort_idx = self.sort_drop.get_selected()
        sort_str = self.sort_drop.get_model().get_string(selected_sort_idx)
        if sort_str == "Highest Rated":
            sort_by = "rating"
        elif sort_str == "Newest First":
            sort_by = "year"
        elif sort_str == "Highest Profit":
            sort_by = "profit"
        else:
            sort_by = "popularity"

        query_params = {
            "query": query,
            "genre": genre,
            "decade": decade,
            "runtime_category": runtime_cat,
            "sort_by": sort_by,
            "limit": 48,
        }

        engine.search_async(query_params, callback=self._render_results)
        return False

    def _render_results(self, results: list[dict[str, Any]]) -> None:
        # Clear grid
        while child := self.grid.get_first_child():
            self.grid.remove(child)

        self.count_lbl.set_text(f"({len(results)} movies displayed)")

        if not results:
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            empty_box.set_margin_top(48)
            empty_box.set_halign(Gtk.Align.CENTER)

            icon = Gtk.Image.new_from_icon_name("system-search-symbolic")
            icon.set_pixel_size(48)
            icon.add_css_class("dim-label")
            empty_box.append(icon)

            lbl = Gtk.Label(label="No movies found matching your filters.")
            lbl.add_css_class("title-4")
            empty_box.append(lbl)

            self.grid.append(empty_box)
            return

        for movie in results:
            card = MovieCard(movie, on_selected=self.on_movie_selected, width=155, height=230)
            self.grid.append(card)
