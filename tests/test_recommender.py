"""
tests/test_recommender.py — Test recommendation algorithms, Bayesian priors, and MMR diversity.
"""

import sys
from pathlib import Path
import pytest
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.recommender import load_model, recommend, recommend_by_mood, _calculate_bayesian_scores, _maximal_marginal_relevance


@pytest.fixture(scope="module")
def model_data():
    processed_dir = PROJECT_ROOT / "data" / "processed"
    return load_model(processed_dir)


def test_load_model(model_data):
    movies_df, similarity = model_data
    assert not movies_df.empty
    assert similarity.shape[0] == len(movies_df)
    assert similarity.shape[1] == len(movies_df)


def test_bayesian_scores(model_data):
    movies_df, _ = model_data
    bayesian_scores = _calculate_bayesian_scores(movies_df)
    assert len(bayesian_scores) == len(movies_df)
    assert 0.0 <= bayesian_scores.min() <= 1.0
    assert 0.0 <= bayesian_scores.max() <= 1.0


def test_mmr_diversity(model_data):
    movies_df, similarity = model_data
    query_scores = similarity[0]
    candidate_indices = list(range(1, 25))
    selected = _maximal_marginal_relevance(
        query_scores=query_scores,
        candidate_indices=candidate_indices,
        similarity_matrix=similarity,
        top_k=5,
        diversity_lambda=0.7,
    )
    assert len(selected) == 5
    assert len(set(selected)) == 5


def test_recommend_by_title(model_data):
    movies_df, similarity = model_data
    # Test recommend for Avatar
    recs = recommend("Avatar", movies_df, similarity, n=5, use_mmr=True)
    assert len(recs) == 5
    for r in recs:
        assert "title" in r
        assert "movie_id" in r
        assert "match_percentage" in r
        assert "match_reason" in r
        assert r["title"] != "Avatar"  # should not recommend itself


def test_recommend_by_id(model_data):
    movies_df, similarity = model_data
    # 19995 is TMDB ID for Avatar
    recs = recommend(19995, movies_df, similarity, n=6)
    assert len(recs) == 6


def test_recommend_by_mood(model_data):
    movies_df, _ = model_data
    recs = recommend_by_mood("mind-bending", movies_df, n=6)
    assert len(recs) > 0
    assert len(recs) <= 6
    for r in recs:
        assert "title" in r
        assert r["vote_average"] > 0


def test_topk_similarity_index_behavior():
    import time
    from src.recommender import TopKSimilarityIndex

    # Create synthetic TopK index
    n_movies = 1000
    k = 50
    indices = np.random.randint(0, n_movies, size=(n_movies, k), dtype=np.int32)
    scores = np.random.uniform(0.5, 1.0, size=(n_movies, k)).astype(np.float16)

    # Set specific known neighbor
    indices[0, 0] = 42
    scores[0, 0] = 0.95

    topk = TopKSimilarityIndex(indices, scores, n_movies=n_movies, k=k)

    assert topk.shape == (1000, 1000)
    assert topk.get_score(0, 0) == 1.0
    assert abs(topk.get_score(0, 42) - 0.95) < 0.01
    assert topk.get_score(0, 999) == 0.0 or indices[0].__contains__(999)

    # 1D row reconstruction
    row0 = topk[0]
    assert len(row0) == 1000
    assert row0[0] == 1.0
    assert abs(row0[42] - 0.95) < 0.01

    # 2D lookup
    assert topk[0, 0] == 1.0

    # Latency test: 1000 lookups should take < 5ms total
    t0 = time.perf_counter()
    for i in range(100):
        _ = topk.get_neighbors(i)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    assert elapsed_ms < 50.0  # Well under limit

