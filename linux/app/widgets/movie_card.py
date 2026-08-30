"""linux/app/widgets/movie_card.py — Interactive Movie Card widget with poster, match badges & rating."""

from __future__ import annotations

from typing import Any, Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gdk, Gtk
from linux.app.image_loader import image_loader


class MovieCard(Gtk.Button):
    """Modern Libadwaita Movie Card displaying poster, title, year, rating and match %."""

    def __init__(
        self,
        movie_data: dict[str, Any],
        on_selected: Callable[[int], None] | None = None,
        width: int = 160,
        height: int = 240,
    ) -> None:
        super().__init__()
        self.movie_data = movie_data
        self.movie_id = int(movie_data["movie_id"])
        self.on_selected = on_selected
        self.card_width = width
        self.card_height = height

        self.add_css_class("movie-card")
        self.add_css_class("flat")
        self.set_cursor_from_name("pointer")
        self.set_size_request(width, -1)

        self._build_card()

        if on_selected:
            self.connect("clicked", lambda _: on_selected(self.movie_id))

    def _build_card(self) -> None:
        root_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        # ── Poster Image Container with Overlay ──────────────────────────────
        overlay = Gtk.Overlay()
        overlay.add_css_class("movie-poster-frame")
        overlay.set_size_request(self.card_width, self.card_height)

        # Picture / Poster
        self.picture = Gtk.Picture()
        self.picture.set_content_fit(Gtk.ContentFit.COVER)
        self.picture.set_size_request(self.card_width, self.card_height)
        
        # Default placeholder icon while loading
        placeholder = Gtk.Image.new_from_icon_name("media-optical-symbolic")
        placeholder.set_pixel_size(48)
        placeholder.add_css_class("dim-label")
        
        frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        frame.set_valign(Gtk.Align.CENTER)
        frame.set_halign(Gtk.Align.CENTER)
        frame.append(placeholder)
        overlay.set_child(frame)

        # Top Badge Bar (Overlay Top)
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        top_bar.set_valign(Gtk.Align.START)
        top_bar.set_halign(Gtk.Align.FILL)
        top_bar.set_margin_top(6)
        top_bar.set_margin_start(6)
        top_bar.set_margin_end(6)

        # Match % Badge (if available)
        match_pct = self.movie_data.get("match_percentage")
        if match_pct is not None:
            pct_val = int(match_pct)
            lbl_match = Gtk.Label(label=f"{pct_val}% Match")
            lbl_match.add_css_class("match-badge-high" if pct_val >= 85 else "match-badge-med")
            top_bar.append(lbl_match)

        # Rating badge
        vote_avg = float(self.movie_data.get("vote_average", 0.0))
        if vote_avg > 0:
            lbl_rating = Gtk.Label(label=f"★ {vote_avg:.1f}")
            lbl_rating.add_css_class("rating-badge")
            lbl_rating.set_halign(Gtk.Align.END)
            lbl_rating.set_hexpand(True)
            top_bar.append(lbl_rating)

        overlay.add_overlay(top_bar)
        root_box.append(overlay)

        # ── Title & Metadata ─────────────────────────────────────────────────
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        title_box.set_margin_start(4)
        title_box.set_margin_end(4)
        title_box.set_margin_bottom(4)

        title = str(self.movie_data.get("title", "Untitled"))
        lbl_title = Gtk.Label(label=title)
        lbl_title.set_wrap(True)
        lbl_title.set_max_width_chars(16)
        lbl_title.set_lines(2)
        lbl_title.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        lbl_title.set_halign(Gtk.Align.START)
        lbl_title.add_css_class("movie-card-title")
        title_box.append(lbl_title)

        year = self.movie_data.get("year")
        genres = self.movie_data.get("genres", [])
        genre_str = genres[0] if genres else "Movie"
        sub_text = f"{year or ''} · {genre_str}" if year else str(genre_str)
        lbl_sub = Gtk.Label(label=sub_text)
        lbl_sub.set_halign(Gtk.Align.START)
        lbl_sub.add_css_class("movie-card-subtitle")
        title_box.append(lbl_sub)

        root_box.append(title_box)
        self.set_child(root_box)

        # ── Async Image Fetch ────────────────────────────────────────────────
        poster_path = self.movie_data.get("poster_path", "")
        if poster_path:
            image_loader.get_texture_async(
                poster_path,
                callback=self._on_poster_loaded,
                is_backdrop=False,
            )

    def _on_poster_loaded(self, texture: Gdk.Texture | None) -> None:
        if texture:
            self.picture.set_paintable(texture)
            # Replace placeholder frame with actual picture
            if overlay := self.get_child().get_first_child():
                overlay.set_child(self.picture)
