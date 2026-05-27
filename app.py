"""
app.py — CineMatch Streamlit entrypoint.

This file is intentionally thin.  All business logic lives in:
  src/recommender.py   — model loading + recommendation
  src/poster.py        — poster fetching (TMDB + OMDb fallback)
  src/preprocessing.py — data pipeline (used by scripts/build_model.py)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

# ── Ensure src/ is importable when launched via `streamlit run app.py` ──────
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.poster import get_poster
from src.recommender import ModelNotFoundError, MovieNotFoundError, load_model, recommend

# ─────────────────────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────────────────────

PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# ─────────────────────────────────────────────────────────────────────────────
# Page config (must be first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CineMatch — Movie Recommender",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background: linear-gradient(135deg, #0d0d1a 0%, #12122a 60%, #0d1b2a 100%);
        color: #e8e8f0;
    }

    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.04);
        border-right: 1px solid rgba(255,255,255,0.08);
    }

    .hero-title {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(90deg, #a78bfa, #60a5fa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1.15;
        margin-bottom: 0.25rem;
    }
    .hero-sub {
        color: #8888aa;
        font-size: 1rem;
        font-weight: 300;
        margin-bottom: 2rem;
    }

    .movie-card {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 0.75rem;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .movie-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(167,139,250,0.18);
    }
    .movie-card img {
        border-radius: 10px;
        width: 100%;
        aspect-ratio: 2/3;
        object-fit: cover;
    }
    .movie-title-text {
        margin-top: 0.6rem;
        font-size: 0.85rem;
        font-weight: 600;
        color: #d0d0e8;
        line-height: 1.3;
    }

    .stButton > button {
        background: linear-gradient(135deg, #a78bfa, #60a5fa);
        color: white;
        border: none;
        padding: 0.65rem 2.5rem;
        border-radius: 50px;
        font-size: 1rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        transition: opacity 0.2s ease, transform 0.2s ease;
        width: 100%;
        margin-top: 0.5rem;
    }
    .stButton > button:hover { opacity: 0.88; transform: scale(1.02); }

    hr { border: none; border-top: 1px solid rgba(255,255,255,0.07); margin: 1.5rem 0; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar — Settings
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## ⚙️ Settings")
    st.markdown("---")

    st.markdown("**🎬 TMDB API Key**")
    tmdb_api_key = st.text_input(
        "TMDB API key",
        value=os.environ.get("TMDB_API_KEY", ""),
        type="password",
        placeholder="Paste your free TMDB key…",
        label_visibility="collapsed",
    )
    st.caption(
        "Get a **free** key at [themoviedb.org/settings/api]"
        "(https://www.themoviedb.org/settings/api). "
        "Without a key, the app falls back to OMDb or a placeholder poster."
    )

    st.markdown("---")
    st.markdown("**📊 Recommendations**")
    num_recs = st.slider("Number of recommendations", min_value=3, max_value=10, value=5)

    st.markdown("---")
    st.markdown("### 🛠️ About")
    st.markdown(
        "Content-based filtering using **CountVectorizer** + **Cosine Similarity** "
        "on TMDB 5000 movie metadata.\n\n"
        "**Model files:** `data/processed/`  \n"
        "**Build script:** `python scripts/build_model.py`"
    )

TMDB_API_KEY = (tmdb_api_key or "").strip()

# ─────────────────────────────────────────────────────────────────────────────
# Data loading (cached per session)
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_resource(show_spinner="Loading recommendation model…")
def _load() -> tuple:
    """Cached model loader — runs once per Streamlit session."""
    try:
        movies_df, similarity = load_model(PROCESSED_DIR)
        return movies_df, similarity, None
    except ModelNotFoundError as exc:
        return None, None, str(exc)


movies_df, similarity, load_error = _load()

# ─────────────────────────────────────────────────────────────────────────────
# Poster fetching (cached)
# ─────────────────────────────────────────────────────────────────────────────


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_poster(movie_id: int, title: str, api_key: str) -> str:
    return get_poster(movie_id, title, api_key)


# ─────────────────────────────────────────────────────────────────────────────
# Main UI
# ─────────────────────────────────────────────────────────────────────────────

st.markdown('<h1 class="hero-title">🎬 CineMatch</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">Discover movies you\'ll love — powered by content-based AI recommendations</p>',
    unsafe_allow_html=True,
)

# ── Error state: model files missing ────────────────────────────────────────
if load_error:
    st.error(
        "**Model files not found.**\n\n"
        "Generate them by running the build script from the project root:\n\n"
        "```bash\npython scripts/build_model.py\n```\n\n"
        f"Details: `{load_error}`"
    )
    st.stop()

# ── Movie selector ───────────────────────────────────────────────────────────
col_sel, col_btn = st.columns([4, 1])
with col_sel:
    selected_movie = st.selectbox(
        "Pick a movie you like",
        options=sorted(movies_df["title"].values),
        index=0,
    )
with col_btn:
    st.markdown("<br>", unsafe_allow_html=True)
    clicked = st.button("✨ Recommend", use_container_width=True)

st.markdown("---")

# ── Results ──────────────────────────────────────────────────────────────────
if clicked:
    try:
        with st.spinner("Finding similar movies…"):
            recs = recommend(selected_movie, movies_df, similarity, n=num_recs)

        st.markdown(f"#### Because you liked **{selected_movie}**, you might enjoy:")

        cols = st.columns(len(recs))
        for col, rec in zip(cols, recs):
            poster_url = _cached_poster(rec["movie_id"], rec["title"], TMDB_API_KEY)
            with col:
                st.markdown(
                    f"""
                    <div class="movie-card">
                        <img src="{poster_url}" alt="{rec['title']}" />
                        <p class="movie-title-text">{rec['title']}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    except MovieNotFoundError as exc:
        st.warning(str(exc))

else:
    # Empty / idle state
    st.markdown(
        """
        <div style="text-align:center; padding: 4rem 0; color: #55557a;">
            <div style="font-size:4rem;">🍿</div>
            <p style="margin-top:1rem; font-size:1.1rem;">
                Select a movie above and hit
                <strong style="color:#a78bfa;">✨ Recommend</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
