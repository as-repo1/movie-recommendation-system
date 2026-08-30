"""linux/app/views/marathon_dialog.py — AI Movie Marathon / Playlist Generator Dialog."""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk
from linux.app.marathon import MovieMarathon, marathon_generator
from linux.app.widgets.movie_card import MovieCard


class MarathonDialog(Adw.Window):
    """Interactive modal to generate and explore 5-movie themed marathons."""

    def __init__(self, parent_window: Gtk.Window, on_movie_selected: Callable[[int], None]) -> None:
        super().__init__()
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_default_size(780, 640)
        self.set_title("AI Mood Marathon Generator")

        self.on_movie_selected = on_movie_selected
        self.selected_moods = ["mind-bending"]

        self._build_ui()
        self._generate_marathon()

    def _build_ui(self) -> None:
        toolbar = Adw.ToolbarView()

        header = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(
            title="🍿 AI Movie Marathon Generator",
            subtitle="Curated 5-film viewing sequences tailored by mood & pacing",
        )
        header.set_title_widget(title_widget)
        toolbar.add_top_bar(header)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        content_box.set_margin_top(14)
        content_box.set_margin_bottom(20)

        # ── Mood Pills Selector ──────────────────────────────────────────────
        selector_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        sel_lbl = Gtk.Label(label="Select Vibe:")
        sel_lbl.add_css_class("stat-box-title")
        sel_lbl.set_valign(Gtk.Align.CENTER)
        selector_box.append(sel_lbl)

        mood_options = [
            ("mind-bending", "🧠 Mind-Bending"),
            ("dark-thriller", "🔪 Dark Thriller"),
            ("feel-good", "☀️ Feel-Good"),
            ("adrenaline", "⚡ Adrenaline"),
            ("epic-journey", "🌌 Epic Journey"),
            ("emotional-drama", "🎭 Emotional"),
        ]

        self.mood_buttons: dict[str, Gtk.Button] = {}
        for slug, name in mood_options:
            btn = Gtk.Button(label=name)
            btn.add_css_class("pill")
            if slug == "mind-bending":
                btn.add_css_class("suggested-action")
            btn.connect("clicked", lambda _, s=slug: self._on_mood_toggled(s))
            selector_box.append(btn)
            self.mood_buttons[slug] = btn

        content_box.append(selector_box)

        # ── Marathon Info Banner ─────────────────────────────────────────────
        self.info_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.info_card.add_css_class("hero-card")

        self.marathon_title_lbl = Gtk.Label(label="Generating Marathon...")
        self.marathon_title_lbl.add_css_class("title-3")
        self.marathon_title_lbl.set_halign(Gtk.Align.START)
        self.info_card.append(self.marathon_title_lbl)

        self.runtime_pill = Gtk.Label(label="")
        self.runtime_pill.add_css_class("rating-badge")
        self.runtime_pill.set_halign(Gtk.Align.END)
        self.runtime_pill.set_hexpand(True)
        self.info_card.append(self.runtime_pill)

        content_box.append(self.info_card)

        # ── Scrollable Marathon Steps List ───────────────────────────────────
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        self.steps_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        scrolled.set_child(self.steps_box)
        content_box.append(scrolled)

        toolbar.set_content(content_box)
        self.set_content(toolbar)

    def _on_mood_toggled(self, slug: str) -> None:
        if slug in self.selected_moods:
            if len(self.selected_moods) > 1:
                self.selected_moods.remove(slug)
                self.mood_buttons[slug].remove_css_class("suggested-action")
        else:
            self.selected_moods.append(slug)
            self.mood_buttons[slug].add_css_class("suggested-action")

        self._generate_marathon()

    def _generate_marathon(self) -> None:
        marathon = marathon_generator.generate_marathon(self.selected_moods, max_movies=5)
        if not marathon:
            return

        self.marathon_title_lbl.set_text(marathon.title)
        hrs = marathon.total_runtime_mins // 60
        mins = marathon.total_runtime_mins % 60
        self.runtime_pill.set_text(f"⏳ Total Runtime: {hrs}h {mins}m")

        # Clear and repopulate steps
        while child := self.steps_box.get_first_child():
            self.steps_box.remove(child)

        for step in marathon.steps:
            step_card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
            step_card.add_css_class("stat-box")

            # Slot Badge
            badge_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            badge_box.set_valign(Gtk.Align.CENTER)
            badge_box.set_size_request(140, -1)

            slot_lbl = Gtk.Label(label=step.slot)
            slot_lbl.add_css_class("stat-box-title")
            slot_lbl.add_css_class("accent")
            slot_lbl.set_halign(Gtk.Align.START)
            badge_box.append(slot_lbl)

            rat_lbl = Gtk.Label(label=step.rationale)
            rat_lbl.add_css_class("caption")
            rat_lbl.add_css_class("dim-label")
            rat_lbl.set_wrap(True)
            rat_lbl.set_halign(Gtk.Align.START)
            badge_box.append(rat_lbl)

            step_card.append(badge_box)

            # Movie Summary Row
            m = step.movie
            m_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            m_box.set_hexpand(True)
            m_box.set_valign(Gtk.Align.CENTER)

            title_lbl = Gtk.Label(label=f"{m['title']} ({m.get('year', '')})")
            title_lbl.add_css_class("heading")
            title_lbl.set_halign(Gtk.Align.START)
            m_box.append(title_lbl)

            meta_lbl = Gtk.Label(label=f"★ {m.get('vote_average', 0.0):.1f} · {', '.join(m.get('genres', [])[:2])} · {m.get('runtime', 110)}m")
            meta_lbl.add_css_class("caption")
            meta_lbl.set_halign(Gtk.Align.START)
            m_box.append(meta_lbl)

            step_card.append(m_box)

            # View Button
            view_btn = Gtk.Button(label="View Details")
            view_btn.add_css_class("pill")
            view_btn.add_css_class("flat")
            view_btn.set_valign(Gtk.Align.CENTER)
            view_btn.connect("clicked", lambda _, mid=m["movie_id"]: self._on_select_movie(mid))
            step_card.append(view_btn)

            self.steps_box.append(step_card)

    def _on_select_movie(self, movie_id: int) -> None:
        self.close()
        self.on_movie_selected(movie_id)
