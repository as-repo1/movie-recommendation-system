"""linux/app/widgets/rating_stars.py — Star rating display and interactive input widget."""

from __future__ import annotations

from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk


class RatingStars(Gtk.Box):
    """Displays 1-5 visual stars with fractional support or interactive click."""

    def __init__(
        self,
        rating_out_of_10: float = 0.0,
        interactive: bool = False,
        on_rating_changed: Callable[[float], None] | None = None,
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.rating_out_of_10 = rating_out_of_10
        self.interactive = interactive
        self.on_rating_changed = on_rating_changed
        self._build_stars()

    def set_rating(self, rating_out_of_10: float) -> None:
        self.rating_out_of_10 = rating_out_of_10
        # Clear children
        while child := self.get_first_child():
            self.remove(child)
        self._build_stars()

    def _build_stars(self) -> None:
        stars_5 = self.rating_out_of_10 / 2.0  # convert 10-scale to 5-scale

        for i in range(1, 6):
            if stars_5 >= i:
                icon_name = "starred-symbolic"
            elif stars_5 >= i - 0.5:
                icon_name = "semi-starred-symbolic"
            else:
                icon_name = "non-starred-symbolic"

            if self.interactive:
                btn = Gtk.Button()
                btn.add_css_class("flat")
                btn.add_css_class("circular")
                img = Gtk.Image.new_from_icon_name(icon_name)
                img.set_pixel_size(16)
                btn.set_child(img)
                star_val = float(i)
                btn.connect("clicked", lambda _, val=star_val: self._on_star_click(val))
                self.append(btn)
            else:
                img = Gtk.Image.new_from_icon_name(icon_name)
                img.set_pixel_size(14)
                if stars_5 >= i - 0.5:
                    img.add_css_class("accent")
                self.append(img)

    def _on_star_click(self, star_val: float) -> None:
        self.rating_out_of_10 = star_val * 2.0
        self.set_rating(self.rating_out_of_10)
        if self.on_rating_changed:
            self.on_rating_changed(star_val)
