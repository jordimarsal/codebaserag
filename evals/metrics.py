import math


# region recall_at_k
def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 0.0
    top = retrieved[:k]
    hits = sum(1 for file in top if file in relevant)
    return hits / len(relevant)


# region reciprocal_rank
def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float:
    for index, file in enumerate(retrieved):
        if file in relevant:
            return 1.0 / (index + 1)
    return 0.0


# region dcg
def dcg(gains: list[float]) -> float:
    return sum(gain / math.log2(index + 2) for index, gain in enumerate(gains))


# region ndcg_at_k
def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    gains = [1.0 if file in relevant else 0.0 for file in retrieved[:k]]
    ideal = [1.0 for _ in range(min(k, len(relevant)))]
    denominator = dcg(ideal)
    if denominator == 0.0:
        return 0.0
    return dcg(gains) / denominator
