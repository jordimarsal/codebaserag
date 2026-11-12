"""Experiment: LlamaIndex store vs the in-memory one.

Same corpus (the repo itself), same deterministic HashEmbedder, same golden
set: the only variable is the `VectorStore` implementation. The experiment
asserts score parity over the whole corpus (every chunk, every query), which
is what proves the adapter faithful.

Recall@5 can still differ slightly when equal-scoring chunks straddle the
cutoff: the port does not define an order for ties, and the two stores break
them differently (llama-index by node id, the in-memory store by insertion
order). That gap is reported, not failed.
"""

from pathlib import Path

from coderag.config import Settings
from coderag.ingest.pipeline import collect_chunks
from coderag.retrieval.bm25 import InMemoryBm25
from coderag.retrieval.retriever import Retriever
from coderag.stores.llamaindex import LlamaIndexStore
from coderag.stores.memory import InMemoryVectorStore
from coderag.stores.ports import VectorStore
from coderag.types import Chunk
from evals.dataset import GoldenEntry, load_golden
from evals.embedder import HashEmbedder
from evals.harness import experiment_markdown, run_retrieval_eval

GOLDEN = Path(__file__).resolve().parents[1] / "golden"
TOP_K = 5
SCORE_TOLERANCE = 1e-12


def load_corpus(settings: Settings) -> tuple[list[Chunk], HashEmbedder, list[list[float]]]:
    chunks = collect_chunks(Path(settings.repo), chunk_size=settings.chunk_size)
    embedder = HashEmbedder()
    return chunks, embedder, embedder.embed([chunk.text for chunk in chunks])


def build_retriever(
    store: VectorStore, chunks: list[Chunk], embedder: HashEmbedder, settings: Settings
) -> Retriever:
    bm25 = InMemoryBm25()
    bm25.index(chunks)
    return Retriever(
        store,
        bm25,
        embedder,
        strategy="dense",
        top_k=TOP_K,
        rerank_top_n=settings.rerank_top_n,
    )


def score_parity(
    entries: list[GoldenEntry], embedder: HashEmbedder, stores: dict[str, VectorStore]
) -> list[str]:
    mismatched: list[str] = []
    for entry in entries:
        vector = embedder.embed([entry.question])[0]
        scores = {
            name: {result.chunk.hash: result.score for result in store.query(vector, store.count())}
            for name, store in stores.items()
        }
        memory = scores["dense (in-memory)"]
        llamaindex = scores["dense (llamaindex)"]
        same_ids = memory.keys() == llamaindex.keys()
        if not same_ids or any(
            abs(memory[chunk_hash] - llamaindex[chunk_hash]) > SCORE_TOLERANCE
            for chunk_hash in memory
        ):
            mismatched.append(entry.question)
    return mismatched


def main() -> int:
    entries = load_golden(GOLDEN)
    settings = Settings()
    chunks, embedder, vectors = load_corpus(settings)
    stores: dict[str, VectorStore] = {
        "dense (in-memory)": InMemoryVectorStore(dim=embedder.dim()),
        "dense (llamaindex)": LlamaIndexStore(dim=embedder.dim()),
    }
    for store in stores.values():
        store.upsert(chunks, vectors)

    reports = {
        name: run_retrieval_eval(
            entries,
            build_retriever(store, chunks, embedder, settings).retrieve,
            top_k=TOP_K,
        )
        for name, store in stores.items()
    }
    print(experiment_markdown(reports))

    mismatched = score_parity(entries, embedder, stores)
    matched = len(entries) - len(mismatched)
    distinct_chunks = len({chunk.hash for chunk in chunks})
    print(
        f"\nscore parity over {distinct_chunks} distinct chunks, {len(entries)} queries: "
        f"{matched}/{len(entries)}"
    )
    for question in mismatched[:3]:
        print(f"  mismatch: {question}")

    recall_gap = abs(
        reports["dense (in-memory)"].mean_recall - reports["dense (llamaindex)"].mean_recall
    )
    print(
        f"recall@5 gap: {recall_gap:.6f} " "(tie-order only; the port leaves tie order unspecified)"
    )
    return 1 if mismatched else 0


if __name__ == "__main__":
    raise SystemExit(main())
