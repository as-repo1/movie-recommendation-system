"""linux/app/window.py — Main Libadwaita Application Window with NavigationSplitView."""

from __future__ import annotations

import logging
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk
from linux.app.engine import engine
from linux.app.state import AppState
from linux.app.views.detail_view import DetailView
from linux.app.views.home_view import HomeView
from linux.app.views.mood_view import MoodView
from linux.app.views.player_view import TrailerPlayerDialog
from linux.app.views.search_view import SearchView
from linux.app.views.watchlist_view import WatchlistView
from linux.app.widgets.spotlight_search import SpotlightSearchDialog

logger = logging.getLogger(__name__)


class RecLensWindow(Adw.ApplicationWindow):
    """Main RecLens desktop application window."""

    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app)
        self.set_title("RecLens — AI Movie Discovery")
        self.add_css_class("main-window")

        self.app_state = AppState.load()
        self.set_default_size(self.app_state.window_width, self.app_state.window_height)
        if self.app_state.window_maximized:
            self.maximize()

        self._nav_history: list[str] = []
        self._current_movie_id: int | None = None

        self._build_ui()
        self._setup_shortcuts()
        self.connect("close-request", self._on_close)

    def _build_ui(self) -> None:
        # ── Root Navigation SplitView ────────────────────────────────────────
        self.split_view = Adw.NavigationSplitView()
        self.split_view.set_min_sidebar_width(220)
        self.split_view.set_max_sidebar_width(260)

        # ── Sidebar ──────────────────────────────────────────────────────────
        sidebar_page = Adw.NavigationPage.new(self._create_sidebar(), "Navigation")
        self.split_view.set_sidebar(sidebar_page)

        # ── Content View Stack & Header ──────────────────────────────────────
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content_box.set_vexpand(True)
        content_box.set_hexpand(True)

        # HeaderBar
        self.header_bar = Adw.HeaderBar()
        self.title_widget = Adw.WindowTitle(title="RecLens", subtitle="AI Movie Discovery")
        self.header_bar.set_title_widget(self.title_widget)

        # Spotlight Search Button (Ctrl+K)
        search_btn = Gtk.Button()
        search_btn.add_css_class("flat")
        search_btn.set_tooltip_text("Instant Spotlight Search (Ctrl+K)")
        search_icon = Gtk.Image.new_from_icon_name("system-search-symbolic")
        search_btn.set_child(search_icon)
        search_btn.connect("clicked", lambda _: self.open_spotlight_search())
        self.header_bar.pack_end(search_btn)

        content_box.append(self.header_bar)

        # View Stack for Pages
        self.view_stack = Adw.ViewStack()
        self.view_stack.set_vexpand(True)
        self.view_stack.set_hexpand(True)


        # 1. Home View
        self.home_view = HomeView(
            on_movie_selected=self.show_movie_detail,
            on_mood_selected=self.show_mood_explorer,
        )
        self.view_stack.add_named(self.home_view, "home")

        # 2. Search & Filter View
        self.search_view = SearchView(
            on_movie_selected=self.show_movie_detail,
        )
        self.view_stack.add_named(self.search_view, "search")

        # 3. Mood Explorer View
        self.mood_view = MoodView(
            on_movie_selected=self.show_movie_detail,
        )
        self.view_stack.add_named(self.mood_view, "mood")

        # 4. Watchlist View
        self.watchlist_view = WatchlistView(
            on_movie_selected=self.show_movie_detail,
            on_explore=lambda: self.switch_view("home"),
        )
        self.view_stack.add_named(self.watchlist_view, "watchlist")

        # Set initial active view
        initial_view = self.app_state.active_view if self.app_state.active_view in ["home", "search", "mood", "watchlist"] else "home"
        self.view_stack.set_visible_child_name(initial_view)

        content_box.append(self.view_stack)
        content_page = Adw.NavigationPage.new(content_box, "Content")
        self.split_view.set_content(content_page)

        self.set_content(self.split_view)

    def _create_sidebar(self) -> Gtk.Widget:
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sidebar_box.set_margin_start(12)
        sidebar_box.set_margin_end(12)
        sidebar_box.set_margin_top(12)
        sidebar_box.set_margin_bottom(16)
        sidebar_box.add_css_class("navigation-sidebar")

        # App Brand Header
        brand_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        brand_box.set_margin_bottom(8)
        brand_box.set_margin_start(6)

        logo = Gtk.Image.new_from_icon_name("org.reclens.RecLens")
        logo.set_pixel_size(28)
        brand_box.append(logo)

        brand_lbl = Gtk.Label(label="RecLens")
        brand_lbl.add_css_class("title-2")
        brand_lbl.add_css_class("accent")
        brand_box.append(brand_lbl)

        sidebar_box.append(brand_box)

        # Nav List Box
        self.nav_list = Gtk.ListBox()
        self.nav_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.nav_list.add_css_class("boxed-list")
        self.nav_list.connect("row-activated", self._on_sidebar_row_activated)

        items = [
            ("home", "Home Discovery", "user-home-symbolic"),
            ("search", "Search & Filters", "system-search-symbolic"),
            ("mood", "Vibe Explorer", "starred-symbolic"),
            ("watchlist", "My Library", "view-paged-symbolic"),
        ]

        self.sidebar_rows: dict[str, Gtk.ListBoxRow] = {}
        for view_name, title, icon_name in items:
            row = Gtk.ListBoxRow()
            row.view_name = view_name

            rbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            rbox.set_margin_top(8)
            rbox.set_margin_bottom(8)
            rbox.set_margin_start(10)
            rbox.set_margin_end(10)

            icon = Gtk.Image.new_from_icon_name(icon_name)
            icon.set_pixel_size(16)
            rbox.append(icon)

            lbl = Gtk.Label(label=title)
            lbl.set_halign(Gtk.Align.START)
            rbox.append(lbl)

            row.set_child(rbox)
            self.nav_list.append(row)
            self.sidebar_rows[view_name] = row

        sidebar_box.append(self.nav_list)

        # Select active row
        active_name = self.app_state.active_view
        if active_name in self.sidebar_rows:
            self.nav_list.select_row(self.sidebar_rows[active_name])
        else:
            self.nav_list.select_row(self.sidebar_rows["home"])

        return sidebar_box

    def _setup_shortcuts(self) -> None:
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_global_key_pressed)
        self.add_controller(key_controller)

    def _on_global_key_pressed(self, controller, keyval, keycode, state) -> bool:
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        if ctrl and (keyval == Gdk.KEY_k or keyval == Gdk.KEY_K or keyval == Gdk.KEY_f or keyval == Gdk.KEY_F):
            self.open_spotlight_search()
            return True
        elif keyval == Gdk.KEY_Escape:
            if self.view_stack.get_visible_child_name() == "detail":
                self._navigate_back()
                return True
        return False

    def _on_sidebar_row_activated(self, list_box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        if hasattr(row, "view_name"):
            self.switch_view(row.view_name)

    def switch_view(self, view_name: str) -> None:
        """Switch view in ViewStack."""
        self._nav_history.append(self.view_stack.get_visible_child_name())
        self.view_stack.set_visible_child_name(view_name)
        self.app_state.active_view = view_name

        if view_name == "watchlist":
            self.watchlist_view.refresh()

        if view_name in self.sidebar_rows:
            self.nav_list.select_row(self.sidebar_rows[view_name])

        subtitles = {
            "home": "AI Movie Discovery",
            "search": "15,000+ Movies Catalog",
            "mood": "Psychological Atmosphere Explorer",
            "watchlist": "Personal Library & History",
        }
        self.title_widget.set_subtitle(subtitles.get(view_name, ""))

    def show_movie_detail(self, movie_id: int) -> None:
        """Navigate to movie detail view."""
        self._nav_history.append(self.view_stack.get_visible_child_name())
        self._current_movie_id = movie_id

        # Remove existing detail page if present
        if existing := self.view_stack.get_child_by_name("detail"):
            self.view_stack.remove(existing)

        detail_view = DetailView(
            movie_id=movie_id,
            on_movie_selected=self.show_movie_detail,
            on_back=self._navigate_back,
            on_watch_trailer=self.open_trailer_player,
        )
        self.view_stack.add_named(detail_view, "detail")
        self.view_stack.set_visible_child_name("detail")

        movie = engine.get_movie_by_id(movie_id)
        if movie:
            self.title_widget.set_subtitle(movie["title"])

    def show_mood_explorer(self, mood_slug: str) -> None:
        """Switch to mood explorer with specific mood active."""
        self.mood_view.set_mood(mood_slug)
        self.switch_view("mood")

    def _navigate_back(self) -> None:
        if self._nav_history:
            prev = self._nav_history.pop()
            self.view_stack.set_visible_child_name(prev)
        else:
            self.switch_view("home")

    def open_spotlight_search(self) -> None:
        """Open the Ctrl+K Spotlight Search dialog."""
        dialog = SpotlightSearchDialog(
            parent_window=self,
            on_movie_selected=self.show_movie_detail,
        )
        dialog.present()

    def open_trailer_player(self, movie_id: int, title: str) -> None:
        """Open embedded trailer video dialog."""
        player = TrailerPlayerDialog(parent_window=self, movie_id=movie_id, movie_title=title)
        player.present()

    def _on_close(self, window: Gtk.Window) -> bool:
        # Save geometry and state
        w, h = self.get_default_size()
        self.app_state.window_width = w
        self.app_state.window_height = h
        self.app_state.window_maximized = self.is_maximized()
        self.app_state.save()
        return False
