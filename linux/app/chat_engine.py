"""linux/app/chat_engine.py — In-process AI Movie Q&A and Contextual Chatbot."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MovieChatEngine:
    """Provides contextual, responsive AI answers for movies in the catalog."""

    def __init__(self, movie_data: dict[str, Any]) -> None:
        self.movie = movie_data
        self.title = movie_data.get("title", "this movie")
        self.year = movie_data.get("year", "")
        self.director = movie_data.get("director", "Unknown Director")
        self.genres = movie_data.get("genres", [])
        self.cast = movie_data.get("cast", [])
        self.overview = movie_data.get("overview", "")
        self.moods = movie_data.get("mood_tags", [])
        self.vote_avg = movie_data.get("vote_average", 0.0)
        self.vote_count = movie_data.get("vote_count", 0)
        self.budget = movie_data.get("budget", 0)
        self.revenue = movie_data.get("revenue", 0)
        self.profit = movie_data.get("profit", 0)

    def answer_question(self, user_query: str) -> str:
        """Analyze question and generate intelligent, structured responses."""
        q = user_query.strip().lower()

        # 1. Who directed / Director style
        if any(w in q for w in ["who directed", "director", "directed by", "filmmaker"]):
            style_desc = f"{self.director} is known for visionary storytelling"
            if "nolan" in self.director.lower():
                style_desc = "Christopher Nolan is renowned for non-linear timelines, practical visual effects, and grand philosophical themes."
            elif "tarantino" in self.director.lower():
                style_desc = "Quentin Tarantino is celebrated for razor-sharp dialogue, stylized violence, and homage to classic cinema."
            elif "spielberg" in self.director.lower():
                style_desc = "Steven Spielberg is an icon of heartfelt emotional journeys, wonder, and epic cinematic setpieces."
            elif "cameron" in self.director.lower():
                style_desc = "James Cameron is famous for groundbreaking cinematic technology, immersive world-building, and massive box office spectacles."

            return f"🎬 **Director:** **{self.director}**\n\n{style_desc}\n\nIn *{self.title}* ({self.year}), their directorial vision shapes the film's unique pacing and visual identity."

        # 2. Cast / Actors / Starring
        if any(w in q for w in ["who stars", "cast", "actors", "actress", "starring", "who is in"]):
            if self.cast:
                top_cast = ", ".join(self.cast[:5])
                return f"🎭 **Lead Cast of {self.title}:**\n\nFeaturing {top_cast}.\n\nThe ensemble delivers compelling performances that anchor the film's emotional and dramatic beats."
            return f"🎭 Cast information for *{self.title}* is being updated in our local catalog."

        # 3. Plot / Story / Summary / What is it about
        if any(w in q for w in ["plot", "story", "summary", "about", "premise", "synopsis"]):
            genres_str = ", ".join(self.genres) if self.genres else "Cinema"
            return f"📖 **Premise of {self.title} ({self.year}):**\n\n{self.overview}\n\n**Genres:** {genres_str}\n**Vibe:** {', '.join(self.moods) if self.moods else 'Engaging Narrative'}"

        # 4. Why should I watch / Is it good / Worth watching / Rating
        if any(w in q for w in ["worth watching", "should i watch", "why watch", "good", "rating", "review"]):
            quality = "Critically Acclaimed Masterpiece" if self.vote_avg >= 8.0 else ("Highly Entertaining & Well Received" if self.vote_avg >= 7.0 else "Interesting Genre Entry")
            reasons = []
            if self.director != "Unknown Director":
                reasons.append(f"Masterful direction by **{self.director}**")
            if self.genres:
                reasons.append(f"Strong execution of the **{', '.join(self.genres[:2])}** genres")
            if self.moods:
                reasons.append(f"Immersive **{self.moods[0]}** vibe and atmosphere")

            reasons_formatted = "\n• " + "\n• ".join(reasons) if reasons else "Engaging characters and strong storytelling."
            return f"⭐ **Verdict: {quality}** (★ {self.vote_avg:.1f}/10 from {self.vote_count:,} ratings)\n\n**Top Reasons to Watch:**{reasons_formatted}\n\nIf you appreciate immersive cinema with memorable sequences, *{self.title}* is well worth your time."

        # 5. Financials / Box office / Budget / Revenue / Profit
        if any(w in q for w in ["box office", "budget", "revenue", "profit", "money", "earn", "gross"]):
            if self.budget > 0 or self.revenue > 0:
                b_str = f"${self.budget / 1_000_000:.1f}M" if self.budget >= 1_000_000 else f"${self.budget:,}"
                r_str = f"${self.revenue / 1_000_000:.1f}M" if self.revenue >= 1_000_000 else f"${self.revenue:,}"
                p_str = f"${self.profit / 1_000_000:+.1f}M" if abs(self.profit) >= 1_000_000 else f"${self.profit:+,}"
                status = "Major Box Office Hit 💰" if self.profit > 100_000_000 else ("Profitable Release" if self.profit > 0 else "Niche / Independent Release")
                return f"📊 **Financial Breakdown for {self.title}:**\n\n• **Budget:** {b_str}\n• **Worldwide Gross:** {r_str}\n• **Net Profit:** {p_str}\n• **Commercial Performance:** {status}"
            return f"📊 Financial records for *{self.title}* are not publicly tracked in the box office registry."

        # 6. Ending explanation / Themes / Meaning
        if any(w in q for w in ["ending", "explained", "theme", "meaning", "message", "symbolism"]):
            genres_str = " & ".join(self.genres[:2]) if self.genres else "human nature"
            return f"🧠 **Themes & Narrative Interpretation:**\n\n*{self.title}* explores profound questions surrounding {genres_str.lower()}.\n\nIts narrative structure challenges audiences to reflect on personal agency, sacrifice, and the consequences of the characters' pivotal choices, creating lasting resonance beyond the credits."

        # 7. Similar movies / What to watch next
        if any(w in q for w in ["similar", "like this", "what next", "recommend", "more like"]):
            return f"🎯 To discover movies with a similar atmosphere to *{self.title}*, check out the **'Similar Masterpieces'** carousel at the bottom of the detail page, or try searching by its vibe (**{self.moods[0] if self.moods else 'Genre'}**) in the Vibe Explorer!"

        # Default contextual response
        return f"💡 **About {self.title} ({self.year}):**\n\nDirected by **{self.director}** and starring **{', '.join(self.cast[:3]) if self.cast else 'acclaimed cast'}**.\n\n{self.overview}\n\n*Feel free to ask about the director, cast, themes, box office stats, or why it's worth watching!*"
