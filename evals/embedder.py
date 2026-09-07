import hashlib


# region HashEmbedder
class HashEmbedder:
    def __init__(self, dim: int = 64) -> None:
        self._dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def dim(self) -> int:
        return self._dim

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = digest[0] % self._dim
            sign = 1.0 if digest[1] % 2 == 0 else -1.0
            vector[index] += sign
        norm = sum(v * v for v in vector) ** 0.5
        if norm > 0.0:
            vector = [v / norm for v in vector]
        return vector
