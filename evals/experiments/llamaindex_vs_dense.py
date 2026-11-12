"""Experiment: dense retrieval over the LlamaIndex store vs the in-memory one.

Same corpus (the repo itself), same deterministic HashEmbedder, same golden
set: the only variable is the `VectorStore` implementation. If the LlamaIndex
adapter is a faithful `VectorStore`, recall@5 matches the in-memory baseline
exactly — any gap is an adapter bug, not retrieval noise.
"""

from pathlib import Path

from coderag.config import Settings
from coderag.ingest.pipeline import collect_chunks
from coderag.retrieval.bm25 import InMemoryBm25
from coderag.retrieval.retriever import Retriever
from coderag.stores.llamaindex import LlamaIndexStore
from coderag.stores.memory import InMemoryVectorStore
from evals.dataset import load_golden
from evals.embedder import HashEmbedder
from evals.harness import experiment_markdown, run_retrieval_eval

GOLDEN = Path(__file__).resolve().parents[1] / "golden"


def build_retriever(settings: Settings, store) -> Retriever:
    chunks = collect_chunks(Path(settings.repo), chunk_size=settings.chunk_size)
    embedder = HashEmbedder()
    store.upsert(chunks, embedder.embed([chunk.text for chunk in chunks]))
    bm25 = InMemoryBm25()
    bm25.index(chunks)
    return Retriever(
        store,
        bm25,
        embedder,
        strategy="dense",
        top_k=5,
        rerank_top_n=settings.rerank_top_n,
    )


def run_experiment() -> str:
    entries = load_golden(GOLDEN)
    settings = Settings()
    variants = {
        "dense (in-memory)": InMemoryVectorStore(dim=HashEmbedder().dim()),
        "dense (llamaindex)": LlamaIndexStore(dim=HashEmbedder().dim()),
    }
    reports = {
        name: run_retrieval_eval(entries, build_retriever(settings, store).retrieve, top_k=5)
        for name, store in variants.items()
    }
    return experiment_markdown(reports)


def main() -> int:
    entries = load_golden(GOLDEN)
    settings = Settings()
    variants = {
        "dense (in-memory)": InMemoryVectorStore(dim=HashEmbedder().dim()),
        "dense (llamaindex)": LlamaIndexStore(dim=HashEmbedder().dim()),
    }
    reports = {
        name: run_retrieval_eval(entries, build_retriever(settings, store).retrieve, top_k=5)
        for name, store in variants.items()
    }
    print(experiment_markdown(reports))

    recalls = {name: report.mean_recall for name, report in reports.items()}
    parity_gap = abs(recalls["dense (llamaindex)"] - recalls["dense (in-memory)"])
    print(f"adapter parity gap: {parity_gap:.6f} (0 = l'adaptador es fidel)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
