"""linux/app/views/home_view.py — Home discovery view with Hero banner, Mood pills, and Carousels."""

from __future__ import annotations

from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk
from linux.app.engine import engine
from linux.app.image_loader import image_loader
from linux.app.widgets.mood_badge import MoodBadge
from linux.app.widgets.movie_card import MovieCard


class HomeView(Gtk.ScrolledWindow):
    """Rich interactive home discovery canvas with Hero spotlight, Mood tags, and Movie Carousels."""

    def __init__(
        self,
        on_movie_selected: Callable[[int], None],
        on_mood_selected: Callable[[str], None],
    ) -> None:
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.on_movie_selected = on_movie_selected
        self.on_mood_selected = on_mood_selected

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        self.main_box.set_vexpand(True)
        self.main_box.set_hexpand(True)
        self.main_box.set_margin_start(24)
        self.main_box.set_margin_end(24)
        self.main_box.set_margin_top(16)
        self.main_box.set_margin_bottom(32)


        self._build_ui()
        self.set_child(self.main_box)

    def _build_ui(self) -> None:
        # ── 1. Hero Spotlight Banner ─────────────────────────────────────────
        hero_movie = engine.get_hero_movie()
        if hero_movie:
            self._build_hero_banner(hero_movie)

        # ── 2. Mood Quick-Picker ─────────────────────────────────────────────
        mood_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        mood_title = Gtk.Label(label="✨ Discover by Vibe & Mood")
        mood_title.set_halign(Gtk.Align.START)
        mood_title.add_css_class("title-3")
        mood_section.append(mood_title)

        moods_flow = Gtk.FlowBox()
        moods_flow.set_valign(Gtk.Align.START)
        moods_flow.set_max_children_per_line(6)
        moods_flow.set_selection_mode(Gtk.SelectionMode.NONE)
        moods_flow.set_column_spacing(10)
        moods_flow.set_row_spacing(8)

        for mood_slug in [
            "mind-bending",
            "dark-thriller",
            "feel-good",
            "adrenaline-action",
            "epic-journey",
            "emotional-drama",
        ]:
            badge = MoodBadge(mood_slug, on_clicked=self.on_mood_selected)
            moods_flow.append(badge)

        mood_section.append(moods_flow)
        self.main_box.append(mood_section)

        # ── 3. Trending Now Carousel ─────────────────────────────────────────
        trending_movies = engine.get_trending(n=12)
        if trending_movies:
            self._build_carousel("🔥 Trending Across the Globe", trending_movies)

        # ── 4. Top Rated Masterpieces Carousel ───────────────────────────────
        top_rated = engine.get_top_rated(n=12)
        if top_rated:
            self._build_carousel("🏆 Critically Acclaimed Masterpieces", top_rated)

        # ── 5. Sci-Fi & Mind-Bending Spotlight ───────────────────────────────
        scifi_movies = engine.get_by_mood("mind-bending", n=12)
        if scifi_movies:
            self._build_carousel("🌌 Mind-Bending & Cosmic Expeditions", scifi_movies)

    def _build_hero_banner(self, movie: dict[str, Any]) -> None:
        hero_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        hero_card.add_css_class("hero-card")

        # Left Info Box
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_box.set_hexpand(True)
        info_box.set_valign(Gtk.Align.CENTER)

        tag_badge = Gtk.Label(label="FEATURED BLOCKBUSTER")
        tag_badge.set_halign(Gtk.Align.START)
        tag_badge.add_css_class("caption")
        tag_badge.add_css_class("accent")
        info_box.append(tag_badge)

        title_lbl = Gtk.Label(label=movie["title"])
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.add_css_class("hero-title")
        info_box.append(title_lbl)

        if movie.get("tagline"):
            tagline_lbl = Gtk.Label(label=f"“{movie['tagline']}”")
            tagline_lbl.set_halign(Gtk.Align.START)
            tagline_lbl.add_css_class("hero-tagline")
            info_box.append(tagline_lbl)

        overview_lbl = Gtk.Label(label=movie.get("overview", ""))
        overview_lbl.set_halign(Gtk.Align.START)
        overview_lbl.set_wrap(True)
        overview_lbl.set_lines(3)
        overview_lbl.set_ellipsize(3)
        overview_lbl.add_css_class("hero-overview")
        info_box.append(overview_lbl)

        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_margin_top(8)

        explore_btn = Gtk.Button(label="Explore Movie Details")
        explore_btn.add_css_class("suggested-action")
        explore_btn.add_css_class("pill")
        explore_btn.connect("clicked", lambda _: self.on_movie_selected(movie["movie_id"]))
        btn_box.append(explore_btn)

        rating_pill = Gtk.Label(label=f"★ {movie.get('vote_average', 0.0):.1f} ({movie.get('vote_count', 0):,} votes)")
        rating_pill.add_css_class("rating-badge")
        rating_pill.set_valign(Gtk.Align.CENTER)
        btn_box.append(rating_pill)

        info_box.append(btn_box)
        hero_card.append(info_box)

        # Right Poster Image
        if movie.get("poster_path"):
            pic = Gtk.Picture()
            pic.set_size_request(130, 195)
            pic.set_content_fit(Gtk.ContentFit.COVER)
            pic.add_css_class("movie-poster-frame")
            image_loader.get_texture_async(movie["poster_path"], callback=lambda tex: tex and pic.set_paintable(tex))
            hero_card.append(pic)

        self.main_box.append(hero_card)

    def _build_carousel(self, title: str, movies: list[dict[str, Any]]) -> None:
        section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)

        title_lbl = Gtk.Label(label=title)
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.add_css_class("title-3")
        section.append(title_lbl)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        scrolled.set_hexpand(True)
        scrolled.set_min_content_height(310)
        scrolled.set_propagate_natural_height(True)


        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        row_box.set_margin_top(4)
        row_box.set_margin_bottom(12)

        for movie in movies:
            card = MovieCard(movie, on_selected=self.on_movie_selected, width=150, height=225)
            row_box.append(card)

        scrolled.set_child(row_box)
        section.append(scrolled)
        self.main_box.append(section)
