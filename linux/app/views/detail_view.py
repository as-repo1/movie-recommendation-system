"""linux/app/views/detail_view.py — Comprehensive Movie Detail view with similar recommendations."""

from __future__ import annotations

from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk
from linux.app.db import local_db
from linux.app.engine import engine
from linux.app.image_loader import image_loader
from linux.app.widgets.mood_badge import MoodBadge
from linux.app.widgets.movie_card import MovieCard
from linux.app.widgets.rating_stars import RatingStars


class DetailView(Gtk.ScrolledWindow):
    """Detailed movie presentation view featuring multi-scores, cast, financial ROI, and similar recommendations."""

    def __init__(
        self,
        movie_id: int,
        on_movie_selected: Callable[[int], None],
        on_back: Callable[[], None],
        on_watch_trailer: Callable[[int, str], None],
    ) -> None:
        super().__init__()
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.movie_id = movie_id
        self.on_movie_selected = on_movie_selected
        self.on_back = on_back
        self.on_watch_trailer = on_watch_trailer

        self.movie_data = engine.get_movie_by_id(movie_id)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.main_box.set_vexpand(True)
        self.main_box.set_hexpand(True)
        self.main_box.set_margin_start(24)
        self.main_box.set_margin_end(24)
        self.main_box.set_margin_top(12)
        self.main_box.set_margin_bottom(32)


        if self.movie_data:
            self._build_ui()
        else:
            self._build_not_found()

        self.set_child(self.main_box)

    def _build_not_found(self) -> None:
        lbl = Gtk.Label(label="Movie details not found.")
        lbl.add_css_class("title-3")
        self.main_box.append(lbl)

    def _build_ui(self) -> None:
        m = self.movie_data

        # ── Navigation Top Bar ───────────────────────────────────────────────
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        back_btn = Gtk.Button()
        back_btn.add_css_class("flat")
        back_btn.add_css_class("circular")
        back_icon = Gtk.Image.new_from_icon_name("go-previous-symbolic")
        back_btn.set_child(back_icon)
        back_btn.connect("clicked", lambda _: self.on_back())
        nav_box.append(back_btn)

        nav_title = Gtk.Label(label="Back to Catalog")
        nav_title.add_css_class("heading")
        nav_box.append(nav_title)
        self.main_box.append(nav_box)

        # ── Hero Section (Backdrop / Poster / Header) ────────────────────────
        hero_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        hero_box.add_css_class("hero-card")

        # Poster Picture
        poster_pic = Gtk.Picture()
        poster_pic.set_size_request(180, 270)
        poster_pic.set_content_fit(Gtk.ContentFit.COVER)
        poster_pic.add_css_class("movie-poster-frame")
        if m.get("poster_path"):
            image_loader.get_texture_async(m["poster_path"], callback=lambda tex: tex and poster_pic.set_paintable(tex))
        hero_box.append(poster_pic)

        # Header Info Box
        header_info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header_info.set_hexpand(True)

        # Title & Year
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title_lbl = Gtk.Label(label=m["title"])
        title_lbl.set_halign(Gtk.Align.START)
        title_lbl.add_css_class("hero-title")
        title_box.append(title_lbl)

        if m.get("year"):
            year_lbl = Gtk.Label(label=f"({m['year']})")
            year_lbl.add_css_class("title-3")
            year_lbl.add_css_class("dim-label")
            title_box.append(year_lbl)
        header_info.append(title_box)

        # Tagline
        if m.get("tagline"):
            tagline = Gtk.Label(label=f"“{m['tagline']}”")
            tagline.set_halign(Gtk.Align.START)
            tagline.add_css_class("hero-tagline")
            header_info.append(tagline)

        # Metadata badges row (Runtime, Genres, Rating)
        meta_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if m.get("runtime"):
            rt_lbl = Gtk.Label(label=f"⏱ {m['runtime']} min ({m.get('runtime_category', 'Feature')})")
            rt_lbl.add_css_class("stat-box-title")
            meta_row.append(rt_lbl)

        for g in m.get("genres", [])[:3]:
            g_lbl = Gtk.Label(label=g)
            g_lbl.add_css_class("rating-badge")
            meta_row.append(g_lbl)

        header_info.append(meta_row)

        # Overview
        if m.get("overview"):
            ov_lbl = Gtk.Label(label=m["overview"])
            ov_lbl.set_halign(Gtk.Align.START)
            ov_lbl.set_wrap(True)
            ov_lbl.add_css_class("hero-overview")
            header_info.append(ov_lbl)

        # Action Buttons Row (Trailer / Watchlist / Watched)
        actions_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        actions_row.set_margin_top(12)

        # 1. Trailer Button
        trailer_btn = Gtk.Button(label="▶ Watch Trailer")
        trailer_btn.add_css_class("suggested-action")
        trailer_btn.add_css_class("pill")
        trailer_btn.connect("clicked", lambda _: self.on_watch_trailer(self.movie_id, m["title"]))
        actions_row.append(trailer_btn)

        # 2. Watchlist Toggle Button
        in_wl = local_db.is_in_watchlist(self.movie_id)
        self.wl_btn = Gtk.Button(label="✓ In Watchlist" if in_wl else "+ Add to Watchlist")
        self.wl_btn.add_css_class("pill")
        if in_wl:
            self.wl_btn.add_css_class("accent")
        self.wl_btn.connect("clicked", self._toggle_watchlist)
        actions_row.append(self.wl_btn)

        # 3. Watched Toggle Button
        is_w = local_db.is_watched(self.movie_id)
        self.watched_btn = Gtk.Button(label="★ Watched" if is_w else "Mark as Watched")
        self.watched_btn.add_css_class("pill")
        self.watched_btn.connect("clicked", self._toggle_watched)
        actions_row.append(self.watched_btn)

        header_info.append(actions_row)
        hero_box.append(header_info)
        self.main_box.append(hero_box)

        # ── Statistics & Financial ROI Bar ───────────────────────────────────
        stats_grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        stats_grid.set_hexpand(True)

        # TMDB Score
        stats_grid.append(self._make_stat_box("TMDB Score", f"★ {m.get('vote_average', 0.0):.1f} / 10", f"{m.get('vote_count', 0):,} votes"))

        # Director
        if m.get("director"):
            stats_grid.append(self._make_stat_box("Director", m["director"], "Head of Direction"))

        # Budget & Revenue
        budget = m.get("budget", 0)
        revenue = m.get("revenue", 0)
        profit = m.get("profit", 0)
        if budget > 0 or revenue > 0:
            rev_str = f"${revenue / 1_000_000:.1f}M" if revenue >= 1_000_000 else f"${revenue:,}"
            prof_str = f"${profit / 1_000_000:+.1f}M" if abs(profit) >= 1_000_000 else f"${profit:+,}"
            stats_grid.append(self._make_stat_box("Box Office", rev_str, f"Profit: {prof_str}"))

        self.main_box.append(stats_grid)

        # ── Cast & Crew Chips ────────────────────────────────────────────────
        if m.get("cast"):
            cast_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            cast_title = Gtk.Label(label="🎭 Top Cast & Characters")
            cast_title.set_halign(Gtk.Align.START)
            cast_title.add_css_class("title-4")
            cast_section.append(cast_title)

            cast_flow = Gtk.FlowBox()
            cast_flow.set_selection_mode(Gtk.SelectionMode.NONE)
            cast_flow.set_column_spacing(8)
            cast_flow.set_row_spacing(6)
            cast_flow.set_max_children_per_line(8)

            for actor in m.get("cast", [])[:8]:
                chip = Gtk.Label(label=actor)
                chip.add_css_class("mood-badge")
                cast_flow.append(chip)

            cast_section.append(cast_flow)
            self.main_box.append(cast_section)

        # ── Similar Movies (MMR + Bayesian Priors) ───────────────────────────
        similar_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sim_title = Gtk.Label(label="🎯 Similar Masterpieces You Might Like")
        sim_title.set_halign(Gtk.Align.START)
        sim_title.add_css_class("title-3")
        similar_section.append(sim_title)

        sim_scrolled = Gtk.ScrolledWindow()
        sim_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        sim_scrolled.set_hexpand(True)

        sim_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        sim_row.set_margin_top(4)
        sim_row.set_margin_bottom(12)

        similar_movies = engine.get_similar(self.movie_id, n=10)
        for sim_movie in similar_movies:
            card = MovieCard(sim_movie, on_selected=self.on_movie_selected, width=150, height=225)
            sim_row.append(card)

        sim_scrolled.set_child(sim_row)
        similar_section.append(sim_scrolled)
        self.main_box.append(similar_section)

    def _make_stat_box(self, title: str, val: str, sub: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.add_css_class("stat-box")
        box.set_hexpand(True)

        lbl_t = Gtk.Label(label=title)
        lbl_t.set_halign(Gtk.Align.START)
        lbl_t.add_css_class("stat-box-title")
        box.append(lbl_t)

        lbl_v = Gtk.Label(label=val)
        lbl_v.set_halign(Gtk.Align.START)
        lbl_v.add_css_class("stat-box-value")
        box.append(lbl_v)

        if sub:
            lbl_s = Gtk.Label(label=sub)
            lbl_s.set_halign(Gtk.Align.START)
            lbl_s.add_css_class("dim-label")
            lbl_s.add_css_class("caption")
            box.append(lbl_s)

        return box

    def _toggle_watchlist(self, btn: Gtk.Button) -> None:
        m = self.movie_data
        if local_db.is_in_watchlist(self.movie_id):
            local_db.remove_from_watchlist(self.movie_id)
            self.wl_btn.set_label("+ Add to Watchlist")
            self.wl_btn.remove_css_class("accent")
        else:
            local_db.add_to_watchlist(
                movie_id=self.movie_id,
                title=m["title"],
                year=m.get("year"),
                poster_path=m.get("poster_path", ""),
                vote_average=m.get("vote_average", 0.0),
            )
            self.wl_btn.set_label("✓ In Watchlist")
            self.wl_btn.add_css_class("accent")

    def _toggle_watched(self, btn: Gtk.Button) -> None:
        m = self.movie_data
        if local_db.is_watched(self.movie_id):
            local_db.remove_from_watched(self.movie_id)
            self.watched_btn.set_label("Mark as Watched")
        else:
            local_db.mark_as_watched(
                movie_id=self.movie_id,
                title=m["title"],
                year=m.get("year"),
                poster_path=m.get("poster_path", ""),
                vote_average=m.get("vote_average", 0.0),
            )
            self.watched_btn.set_label("★ Watched")
            self.wl_btn.set_label("+ Add to Watchlist")
            self.wl_btn.remove_css_class("accent")
