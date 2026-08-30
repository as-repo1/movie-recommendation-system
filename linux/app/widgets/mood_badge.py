"""linux/app/widgets/mood_badge.py — Pill-shaped mood & vibe badge widget."""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk


class MoodBadge(Gtk.Button):
    """Clickable mood badge pill with icon and label."""

    MOOD_ICONS = {
        "mind-bending": "emblem-synchronizing-symbolic",
        "dark-thriller": "dialog-warning-symbolic",
        "feel-good": "starred-symbolic",
        "adrenaline-action": "media-playback-start-symbolic",
        "epic-journey": "view-paged-symbolic",
        "emotional-drama": "heart-symbolic",
    }

    MOOD_LABELS = {
        "mind-bending": "Mind-Bending",
        "dark-thriller": "Dark Thriller",
        "feel-good": "Feel-Good",
        "adrenaline-action": "Adrenaline Action",
        "epic-journey": "Epic Journey",
        "emotional-drama": "Emotional Drama",
    }

    def __init__(self, mood_slug: str, on_clicked: Callable[[str], None] | None = None) -> None:
        super().__init__()
        self.mood_slug = mood_slug
        self.on_clicked_callback = on_clicked
        self.add_css_class("mood-badge")
        self.set_cursor_from_name("pointer")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        icon_name = self.MOOD_ICONS.get(mood_slug, "starred-symbolic")
        icon = Gtk.Image.new_from_icon_name(icon_name)
        icon.set_pixel_size(14)
        box.append(icon)

        label_text = self.MOOD_LABELS.get(mood_slug, mood_slug.replace("-", " ").title())
        lbl = Gtk.Label(label=label_text)
        box.append(lbl)

        self.set_child(box)

        if on_clicked:
            self.connect("clicked", lambda _: on_clicked(self.mood_slug))
