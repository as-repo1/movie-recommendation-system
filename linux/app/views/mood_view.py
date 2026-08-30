"""linux/app/views/mood_view.py — Psychological Mood & Vibe discovery explorer."""

from __future__ import annotations

from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk
from linux.app.engine import engine
from linux.app.widgets.movie_card import MovieCard


class MoodView(Gtk.ScrolledWindow):
    """Mood explorer view offering 6 distinct psychological vibe channels."""

    MOOD_DETAILS = {
        "mind-bending": {
            "title": "Mind-Bending & Cosmic Sci-Fi",
            "desc": "Complex narratives, time loops, parallel realities, and existential sci-fi mysteries.",
            "icon": "emblem-synchronizing-symbolic",
        },
        "dark-thriller": {
            "title": "Dark & Gritty Thrillers",
            "desc": "High-stakes neo-noirs, psychological cat-and-mouse suspense, and intense crime sagas.",
            "icon": "dialog-warning-symbolic",
        },
        "feel-good": {
            "title": "Heartwarming & Feel-Good",
            "desc": "Uplifting stories, witty comedies, feel-good adventures, and nostalgic charm.",
            "icon": "starred-symbolic",
        },
        "adrenaline-action": {
            "title": "Adrenaline & High-Octane Action",
            "desc": "Fast-paced thrillers, kinetic choreography, martial arts, and relentless chases.",
            "icon": "media-playback-start-symbolic",
        },
        "epic-journey": {
            "title": "Epic Mythologies & Grand Journeys",
            "desc": "Sweeping fantasy landscapes, legendary quests, historical battles, and mythic sagas.",
            "icon": "view-paged-symbolic",
        },
        "emotional-drama": {
            "title": "Poignant & Emotional Dramas",
            "desc": "Deep character studies, touching relationships, tears, and human resilience.",
            "icon": "heart-symbolic",
        },
    }

    def __init__(
        self,
        on_movie_selected: Callable[[int], None],
        initial_mood: str = "mind-bending",
    ) -> None:
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.on_movie_selected = on_movie_selected
        self.active_mood = initial_mood

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_box.set_vexpand(True)
        self.main_box.set_hexpand(True)
        self.main_box.set_margin_start(24)
        self.main_box.set_margin_end(24)
        self.main_box.set_margin_top(16)
        self.main_box.set_margin_bottom(32)


        self._build_ui()
        self.set_child(self.main_box)
        self.set_mood(initial_mood)

    def _build_ui(self) -> None:
        # ── Title ────────────────────────────────────────────────────────────
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_lbl = Gtk.Label(label="✨ Vibe & Mood Explorer")
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.add_css_class("title-2")
        header_box.append(title_lbl)

        sub_lbl = Gtk.Label(label="Select a psychological mood to filter by narrative atmosphere and thematic intensity.")
        sub_lbl.set_halign(Gtk.Align.START)
        sub_lbl.add_css_class("dim-label")
        header_box.append(sub_lbl)

        self.main_box.append(header_box)

        # ── Mood Pills Switcher ──────────────────────────────────────────────
        pills_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pills_box.set_hexpand(True)

        self.mood_buttons: dict[str, Gtk.Button] = {}
        for slug, meta in self.MOOD_DETAILS.items():
            btn = Gtk.Button(label=meta["title"].split("&")[0].strip())
            btn.add_css_class("pill")
            btn.connect("clicked", lambda _, s=slug: self.set_mood(s))
            pills_box.append(btn)
            self.mood_buttons[slug] = btn

        self.main_box.append(pills_box)

        # ── Active Mood Description Banner ───────────────────────────────────
        self.banner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.banner.add_css_class("stat-box")
        self.banner.set_margin_top(4)

        self.banner_title = Gtk.Label()
        self.banner_title.set_halign(Gtk.Align.START)
        self.banner_title.add_css_class("title-3")
        self.banner_title.add_css_class("accent")
        self.banner.append(self.banner_title)

        self.banner_desc = Gtk.Label()
        self.banner_desc.set_halign(Gtk.Align.START)
        self.banner_desc.add_css_class("dim-label")
        self.banner_desc.set_wrap(True)
        self.banner.append(self.banner_desc)

        self.main_box.append(self.banner)

        # ── Movies Grid ──────────────────────────────────────────────────────
        self.grid = Gtk.FlowBox()
        self.grid.set_valign(Gtk.Align.START)
        self.grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self.grid.set_column_spacing(16)
        self.grid.set_row_spacing(20)
        self.grid.set_min_children_per_line(2)
        self.grid.set_max_children_per_line(8)
        self.main_box.append(self.grid)

    def set_mood(self, mood_slug: str) -> None:
        """Switch active mood and refresh movie cards."""
        self.active_mood = mood_slug
        meta = self.MOOD_DETAILS.get(mood_slug, self.MOOD_DETAILS["mind-bending"])

        # Update button active styles
        for s, btn in self.mood_buttons.items():
            if s == mood_slug:
                btn.add_css_class("suggested-action")
            else:
                btn.remove_css_class("suggested-action")

        # Update banner text
        self.banner_title.set_text(meta["title"])
        self.banner_desc.set_text(meta["desc"])

        # Fetch and render movies
        movies = engine.get_by_mood(mood_slug, n=24)
        self._render_movies(movies)

    def _render_movies(self, movies: list[dict[str, Any]]) -> None:
        while child := self.grid.get_first_child():
            self.grid.remove(child)

        for movie in movies:
            card = MovieCard(movie, on_selected=self.on_movie_selected, width=155, height=230)
            self.grid.append(card)
