"""linux/app/theme_manager.py — Dynamic Theme Management for RecLens Desktop."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk

logger = logging.getLogger(__name__)


@dataclass
class ThemeDefinition:
    id: str
    name: str
    description: str
    is_dark: bool
    accent_color: str
    accent_fg: str
    card_bg: str
    window_bg: str
    window_fg: str
    badge_bg: str


THEMES: dict[str, ThemeDefinition] = {
    "catppuccin": ThemeDefinition(
        id="catppuccin",
        name="Catppuccin Mocha",
        description="Modern Violet & Lavender Dark",
        is_dark=True,
        accent_color="#89b4fa",
        accent_fg="#11111b",
        card_bg="#181825",
        window_bg="#1e1e2e",
        window_fg="#cdd6f4",
        badge_bg="rgba(137, 180, 250, 0.2)",
    ),
    "nord": ThemeDefinition(
        id="nord",
        name="Nord Frost",
        description="Arctic Slate & Ice Blue",
        is_dark=True,
        accent_color="#88c0d0",
        accent_fg="#2e3440",
        card_bg="#3b4252",
        window_bg="#2e3440",
        window_fg="#eceff4",
        badge_bg="rgba(136, 192, 208, 0.2)",
    ),
    "dracula": ThemeDefinition(
        id="dracula",
        name="Dracula Pro",
        description="Vibrant Neon Purple & Pink",
        is_dark=True,
        accent_color="#bd93f9",
        accent_fg="#282a36",
        card_bg="#343746",
        window_bg="#282a36",
        window_fg="#f8f8f2",
        badge_bg="rgba(189, 147, 249, 0.2)",
    ),
    "oled": ThemeDefinition(
        id="oled",
        name="OLED Midnight Black",
        description="True Black #000000 & Electric Cyan",
        is_dark=True,
        accent_color="#00f0ff",
        accent_fg="#000000",
        card_bg="#0d0d0d",
        window_bg="#000000",
        window_fg="#ffffff",
        badge_bg="rgba(0, 240, 255, 0.2)",
    ),
    "sunset": ThemeDefinition(
        id="sunset",
        name="Sunset Amber",
        description="Warm Cinema Gold & Bronze",
        is_dark=True,
        accent_color="#fab387",
        accent_fg="#181825",
        card_bg="#1e1d2d",
        window_bg="#181825",
        window_fg="#cdd6f4",
        badge_bg="rgba(250, 179, 135, 0.2)",
    ),
    "adwaita_light": ThemeDefinition(
        id="adwaita_light",
        name="Adwaita Clean Light",
        description="Crisp Studio Light Canvas",
        is_dark=False,
        accent_color="#1c71d8",
        accent_fg="#ffffff",
        card_bg="#ffffff",
        window_bg="#f6f6f6",
        window_fg="#2e3436",
        badge_bg="rgba(28, 113, 216, 0.15)",
    ),
}


class ThemeManager:
    """Manages active theme palette, CSS injection, and Libadwaita color scheme."""

    def __init__(self) -> None:
        self.active_theme_id: str = "catppuccin"
        self._provider: Gtk.CssProvider | None = None
        self._listeners: list[Callable[[str], None]] = []

    def get_theme(self, theme_id: str | None = None) -> ThemeDefinition:
        tid = theme_id or self.active_theme_id
        return THEMES.get(tid, THEMES["catppuccin"])

    def get_all_themes(self) -> list[ThemeDefinition]:
        return list(THEMES.values())

    def apply_theme(self, theme_id: str) -> None:
        """Apply selected theme to GTK display and Libadwaita StyleManager."""
        if theme_id not in THEMES:
            theme_id = "catppuccin"

        self.active_theme_id = theme_id
        theme = THEMES[theme_id]

        # 1. Update Libadwaita Color Scheme
        style_mgr = Adw.StyleManager.get_default()
        if theme.is_dark:
            style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        else:
            style_mgr.set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)

        # 2. Build Dynamic CSS Variables
        css = f"""
        @define-color accent_color {theme.accent_color};
        @define-color accent_bg_color {theme.accent_color};
        @define-color accent_fg_color {theme.accent_fg};
        @define-color window_bg_color {theme.window_bg};
        @define-color window_fg_color {theme.window_fg};
        @define-color card_bg_color {theme.card_bg};
        @define-color card_fg_color {theme.window_fg};

        window.main-window {{
            background-color: {theme.window_bg};
            color: {theme.window_fg};
        }}

        .hero-card {{
            background: linear-gradient(135deg, {theme.badge_bg}, {theme.card_bg});
            border: 1px solid {theme.badge_bg};
        }}

        .movie-card {{
            background-color: {theme.card_bg};
        }}

        .movie-card:hover {{
            background-color: {theme.badge_bg};
            border-color: {theme.accent_color};
        }}

        .mood-badge {{
            background-color: {theme.badge_bg};
            color: {theme.accent_color};
            border-color: {theme.accent_color};
        }}
        """

        display = Gdk.Display.get_default()
        if display:
            if self._provider:
                Gtk.StyleContext.remove_provider_for_display(display, self._provider)

            self._provider = Gtk.CssProvider()
            self._provider.load_from_data(css.encode("utf-8"))
            Gtk.StyleContext.add_provider_for_display(
                display,
                self._provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10,
            )

        for listener in self._listeners:
            try:
                listener(theme_id)
            except Exception as e:
                logger.warning("Theme listener failed: %s", e)

    def add_listener(self, callback: Callable[[str], None]) -> None:
        self._listeners.append(callback)


# Singleton
theme_manager = ThemeManager()
