from evals.metrics import dcg, ndcg_at_k, recall_at_k, reciprocal_rank


def test_recall_at_k_perfect() -> None:
    assert recall_at_k(["a.py", "b.py"], {"a.py", "b.py"}, 5) == 1.0


def test_recall_at_k_partial() -> None:
    assert recall_at_k(["a.py", "x.py"], {"a.py", "b.py"}, 5) == 0.5


def test_recall_at_k_truncated_by_k() -> None:
    assert recall_at_k(["a.py"], {"a.py", "b.py"}, 1) == 0.5


def test_recall_at_k_empty_relevant() -> None:
    assert recall_at_k(["a.py"], set(), 5) == 0.0


def test_recall_at_k_no_hits() -> None:
    assert recall_at_k(["z.py"], {"a.py", "b.py"}, 5) == 0.0


def test_reciprocal_rank_first_hit() -> None:
    assert reciprocal_rank(["a.py", "b.py"], {"a.py"}) == 1.0


def test_reciprocal_rank_second_hit() -> None:
    assert reciprocal_rank(["x.py", "a.py"], {"a.py"}) == 0.5


def test_reciprocal_rank_no_hit() -> None:
    assert reciprocal_rank(["x.py"], {"a.py"}) == 0.0


def test_dcg_basic() -> None:
    # gain 1 at rank0 -> 1/log2(2)=1 ; rank1 gain1 -> 1/log2(3)~0.63
    assert dcg([1.0, 1.0]) > 1.0


def test_ndcg_perfect() -> None:
    assert ndcg_at_k(["a.py", "b.py"], {"a.py", "b.py"}, 5) == 1.0


def test_ndcg_zero_when_irrelevant() -> None:
    assert ndcg_at_k(["x.py", "y.py"], {"a.py", "b.py"}, 5) == 0.0


def test_ndcg_partial() -> None:
    score = ndcg_at_k(["a.py", "x.py"], {"a.py", "b.py"}, 5)
    assert 0.0 < score < 1.0
