"""linux/app/views/chat_dialog.py — In-app AI Movie Chat & Q&A Dialog."""

from __future__ import annotations

import logging
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk
from linux.app.chat_engine import MovieChatEngine

logger = logging.getLogger(__name__)


class MovieChatDialog(Adw.Window):
    """Interactive AI Chatbot Dialog for exploring movie trivia, themes, and questions."""

    def __init__(self, parent_window: Gtk.Window, movie_data: dict[str, Any]) -> None:
        super().__init__()
        self.set_transient_for(parent_window)
        self.set_modal(True)
        self.set_destroy_with_parent(True)
        self.set_default_size(700, 600)
        self.set_title(f"Chat AI — {movie_data.get('title', 'Movie')}")
        self.add_css_class("chat-dialog-window")

        self.movie_data = movie_data
        self.engine = MovieChatEngine(movie_data)

        self._build_ui()
        # Add welcome bot greeting
        self._add_bot_message(
            f"👋 Hello! I'm your AI Movie Companion for **{movie_data.get('title')}** ({movie_data.get('year')}).\n\nAsk me anything: plot questions, director trivia, cast details, themes, or why you should watch it!"
        )

    def _build_ui(self) -> None:
        toolbar = Adw.ToolbarView()

        # HeaderBar
        header = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(
            title=f"Chat AI — {self.movie_data.get('title')}",
            subtitle="Ask questions & explore cinematic insights",
        )
        header.set_title_widget(title_widget)
        toolbar.add_top_bar(header)

        # Main Container
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_vexpand(True)
        content_box.set_hexpand(True)
        content_box.set_margin_start(18)
        content_box.set_margin_end(18)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(16)

        # Quick Suggested Questions Pills
        quick_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        quick_lbl = Gtk.Label(label="💡 Quick Ask:")
        quick_lbl.add_css_class("stat-box-title")
        quick_box.append(quick_lbl)

        suggestions = [
            "Why should I watch this?",
            "Who directed & what is their style?",
            "What are the main themes?",
            "Box office breakdown",
        ]
        for s in suggestions:
            btn = Gtk.Button(label=s)
            btn.add_css_class("flat")
            btn.add_css_class("rating-badge")
            btn.connect("clicked", lambda _, q=s: self._send_user_message(q))
            quick_box.append(btn)

        quick_scrolled = Gtk.ScrolledWindow()
        quick_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        quick_scrolled.set_min_content_height(44)
        quick_scrolled.set_propagate_natural_height(True)
        quick_scrolled.set_child(quick_box)
        content_box.append(quick_scrolled)


        # Chat Messages Scrolled Window
        self.chat_scrolled = Gtk.ScrolledWindow()
        self.chat_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.chat_scrolled.set_vexpand(True)
        self.chat_scrolled.set_hexpand(True)

        self.messages_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        self.messages_box.set_margin_top(8)
        self.messages_box.set_margin_bottom(8)
        self.chat_scrolled.set_child(self.messages_box)
        content_box.append(self.chat_scrolled)

        # Bottom Entry & Send Row
        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Ask a question about this movie (Press Enter)...")
        self.entry.set_hexpand(True)
        self.entry.add_css_class("spotlight-entry")
        self.entry.connect("activate", self._on_entry_activate)
        input_row.append(self.entry)

        send_btn = Gtk.Button(label="Send")
        send_btn.add_css_class("suggested-action")
        send_btn.add_css_class("pill")
        send_btn.connect("clicked", lambda _: self._on_entry_activate(self.entry))
        input_row.append(send_btn)

        content_box.append(input_row)

        toolbar.set_content(content_box)
        self.set_content(toolbar)

    def _on_entry_activate(self, entry: Gtk.Entry) -> None:
        text = entry.get_text().strip()
        if not text:
            return
        entry.set_text("")
        self._send_user_message(text)

    def _send_user_message(self, text: str) -> None:
        # Add User Message Bubble
        user_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        user_row.set_halign(Gtk.Align.END)

        bubble = Gtk.Label(label=text)
        bubble.set_wrap(True)
        bubble.set_max_width_chars(50)
        bubble.add_css_class("suggested-action")
        bubble.add_css_class("pill")
        bubble.set_margin_start(40)
        user_row.append(bubble)

        self.messages_box.append(user_row)
        self._scroll_to_bottom()

        # Generate Bot Answer
        answer = self.engine.answer_question(text)
        GLib.timeout_add(150, lambda: self._add_bot_message(answer))

    def _add_bot_message(self, text: str) -> bool:
        bot_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bot_row.set_halign(Gtk.Align.START)

        avatar = Gtk.Image.new_from_icon_name("starred-symbolic")
        avatar.set_pixel_size(24)
        avatar.add_css_class("accent")
        avatar.set_valign(Gtk.Align.START)
        bot_row.append(avatar)

        bubble = Gtk.Label(label=text)
        bubble.set_wrap(True)
        bubble.set_max_width_chars(60)
        bubble.set_selectable(True)
        bubble.add_css_class("stat-box")
        bubble.set_margin_end(30)
        bot_row.append(bubble)

        self.messages_box.append(bot_row)
        self._scroll_to_bottom()
        return False

    def _scroll_to_bottom(self) -> None:
        GLib.idle_add(lambda: self.chat_scrolled.get_vadjustment().set_value(
            self.chat_scrolled.get_vadjustment().get_upper()
        ))
