"""
streamlit_app.py — CineMatch Streamlit UI.
A standalone, interactive movie recommendation web interface.
Features:
- Content-Based & Bayesian Quality Filtered Recommendations
- Mood & Vibe Explorer (Mind-Bending, Dark Thriller, Feel-Good, Action, Epic)
- Director, Cast, and Genre Match Details
- Live TMDB / OMDb Poster Resolution & Fallbacks
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.poster import get_poster
from src.recommender import (
    ModelNotFoundError,
    MovieNotFoundError,
    load_model,
    recommend,
    recommend_by_mood,
)

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ─────────────────────────────────────────────────────────────────────────────
# Page Config & Styles
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CineMatch — AI Movie Recommender",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at 50% 0%, #1a1b2e 0%, #0e1017 65%, #08090d 100%);
        color: #eceff4;
    }

    [data-testid="stSidebar"] {
        background: rgba(20, 23, 33, 0.85);
        border-right: 1px solid rgba(255,255,255,0.08);
        backdrop-filter: blur(16px);
    }

    .hero-title {
        font-family: 'Outfit', sans-serif;
        font-size: 3.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #88c0d0 0%, #81a1c1 50%, #b48ead 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.15;
        margin-bottom: 0.35rem;
        letter-spacing: -1px;
    }

    .hero-sub {
        color: #94a3b8;
        font-size: 1.05rem;
        font-weight: 400;
        margin-bottom: 2rem;
    }

    .movie-card {
        background: rgba(30, 36, 51, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 0.85rem;
        text-align: center;
        transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.22s ease;
        backdrop-filter: blur(8px);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .movie-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 16px 36px rgba(136, 192, 208, 0.18);
        border-color: rgba(136, 192, 208, 0.4);
    }

    .movie-card img {
        border-radius: 10px;
        width: 100%;
        aspect-ratio: 2/3;
        object-fit: cover;
    }

    .movie-title-text {
        margin-top: 0.75rem;
        font-size: 0.9rem;
        font-weight: 600;
        color: #e2e8f0;
        line-height: 1.35;
    }

    .match-chip {
        display: inline-block;
        background: rgba(136, 192, 208, 0.15);
        color: #88c0d0;
        border: 1px solid rgba(136, 192, 208, 0.3);
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.74rem;
        font-weight: 700;
        margin-top: 4px;
    }

    .reason-text {
        color: #94a3b8;
        font-size: 0.75rem;
        margin-top: 4px;
    }

    .stButton > button {
        background: linear-gradient(135deg, #88c0d0, #5e81ac);
        color: #0f141c;
        border: none;
        padding: 0.7rem 2.5rem;
        border-radius: 50px;
        font-size: 1.02rem;
        font-weight: 700;
        letter-spacing: 0.3px;
        transition: transform 0.18s ease, filter 0.18s ease;
        width: 100%;
    }

    .stButton > button:hover {
        filter: brightness(1.15);
        transform: scale(1.02);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Model Caching
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_resource(show_spinner="Loading RecLens recommendation engine…")
def _load():
    try:
        movies_df, similarity = load_model(PROCESSED_DIR)
        return movies_df, similarity, None
    except ModelNotFoundError as exc:
        return None, None, str(exc)


movies_df, similarity, load_error = _load()


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_poster(movie_id: int, title: str, api_key: str) -> str:
    return get_poster(movie_id, title, api_key)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🎬 RecLens")
    st.caption("AI-Powered Hybrid Recommendation System")
    st.markdown("---")

    st.markdown("**🔑 TMDB API Key (Optional)**")
    tmdb_key_input = st.text_input(
        "TMDB API Key",
        value=os.environ.get("TMDB_API_KEY", ""),
        type="password",
        placeholder="Paste TMDB key for dynamic posters…",
        label_visibility="collapsed",
    )
    TMDB_API_KEY = (tmdb_key_input or "").strip()

    st.markdown("---")
    st.markdown("**⚙️ Recommendation Settings**")
    num_recs = st.slider("Number of recommendations", min_value=4, max_value=12, value=6)
    use_mmr = st.checkbox("Enable Diversity Re-ranking (MMR)", value=True)

    st.markdown("---")
    st.markdown("### 📊 Engine Details")
    st.markdown(
        "- **Algorithms**: TF-IDF (8000 bi-gram features) + Cosine Similarity\n"
        "- **Quality Prior**: Bayesian Weighted Rating Boost ($WR$)\n"
        "- **Diversity**: Maximal Marginal Relevance ($\lambda=0.75$)\n"
        "- **Dataset**: TMDB 5000 + MovieLens Hybrid"
    )

# ─────────────────────────────────────────────────────────────────────────────
# Main Layout
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<h1 class="hero-title">🎬 CineMatch</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">Discover films tailored to your cinematic taste with explainable AI</p>',
    unsafe_allow_html=True,
)

if load_error:
    st.error(
        f"**Model files not found.**\n\nRun the build script:\n```bash\npython scripts/build_model.py\n```\n\nDetails: `{load_error}`"
    )
    st.stop()

# Mode selection
tab_similar, tab_mood = st.tabs(["✨ Movie-Based Recommendations", "🌟 Mood & Vibe Explorer"])

with tab_similar:
    col1, col2 = st.columns([4, 1])
    with col1:
        selected_movie = st.selectbox(
            "Select a movie you enjoyed",
            options=sorted(movies_df["title"].values),
            index=0,
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        clicked = st.button("✨ Recommend", use_container_width=True)

    if clicked:
        try:
            with st.spinner("Analyzing semantic themes & directing styles…"):
                recs = recommend(
                    selected_movie,
                    movies_df,
                    similarity,
                    n=num_recs,
                    use_mmr=use_mmr,
                )

            st.markdown(f"### Because you liked **{selected_movie}**:")
            cols = st.columns(len(recs))
            for col, rec in zip(cols, recs):
                poster_url = _cached_poster(rec["movie_id"], rec["title"], TMDB_API_KEY)
                with col:
                    match_pct = rec.get("match_percentage", 90)
                    reason = rec.get("match_reason", "")
                    st.markdown(
                        f"""
                        <div class="movie-card">
                            <img src="{poster_url}" alt="{rec['title']}" />
                            <div>
                                <p class="movie-title-text">{rec['title']}</p>
                                <span class="match-chip">{match_pct}% Match</span>
                                <p class="reason-text">{reason}</p>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
        except MovieNotFoundError as exc:
            st.warning(str(exc))

with tab_mood:
    st.markdown("#### Pick a vibe for tonight:")
    mood_options = {
        "🧠 Mind-Bending Sci-Fi & Mystery": "mind-bending",
        "🕵️ Dark & Gritty Thrillers": "dark-thriller",
        "🍿 Heartwarming & Feel-Good": "feel-good",
        "⚡ Adrenaline & High-Octane Action": "adrenaline-action",
        "🏰 Epic Journeys & Fantasy": "epic-journey",
        "❤️ Emotional & Romantic Drama": "emotional-drama",
    }
    selected_mood_label = st.radio(
        "Choose mood",
        options=list(mood_options.keys()),
        horizontal=True,
        label_visibility="collapsed",
    )
    mood_key = mood_options[selected_mood_label]

    with st.spinner("Finding top picks for this mood…"):
        mood_recs = recommend_by_mood(mood_key, movies_df, n=num_recs)

    if mood_recs:
        cols = st.columns(len(mood_recs))
        for col, rec in zip(cols, mood_recs):
            poster_url = _cached_poster(rec["movie_id"], rec["title"], TMDB_API_KEY)
            with col:
                st.markdown(
                    f"""
                    <div class="movie-card">
                        <img src="{poster_url}" alt="{rec['title']}" />
                        <div>
                            <p class="movie-title-text">{rec['title']}</p>
                            <span class="match-chip">{rec.get('vote_average', 0):.1f} ★</span>
                            <p class="reason-text">Top {mood_key.replace('-', ' ')} pick</p>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
