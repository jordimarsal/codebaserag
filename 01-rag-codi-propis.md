# Projecte 1 — RAG sobre codi propi (`codebase-rag`)

 Projecte 1 (RAG) — hexagonal + pipeline de transforms purs:
     - Core pur: chunking, fusió RRF, muntatge de prompt, càlcul de citacions — funcions        deterministes sense xarxa.
     - Ports: VectorStore, Embedder, LlmClient, Reranker com a Protocol; adapters pgvector/Qdrant/
       Ollama/Anthropic.
     - Tres subdominis separats (ingest / retrieval / generation) amb el store com a únic punt        d'acoblament — l'ingest pot córrer com a CLI i el retrieval com a FastAPI sense compartir codi d'I/O.
     - Per què: necessites intercanviar components per als experiments (ADR-001 chunking, etc.) i
       evals deterministes del core sense mock de xarxa.

> **Elevat pitch:** un RAG que indexa els teus propis repositoris (codi, docs, ADRs, issues)
> i respon preguntes amb citacions verificables — "on es gestiona el rate limiting?",
> "com es propaga aquest error?", "quin ADR va decidir això?" — amb evals i traçabilitat
> de primera classe des del dia u.

---

## 1. Per què aquest projecte

Requisits de l'oferta que ataca directament:

| Requisit | Com el cobreix |
|---|---|
| Sistemes LLM en producció (RAG, pipelines) | Pipeline d'ingestió + recuperació + generació complet, desplegat amb Docker |
| Vector DBs (pgvector, Qdrant...) | Comparativa real entre 2 stores amb el mateix corpus i les mateixes evals |
| RAG patterns (chunking, retrieval, reranking) | Experiments mesurats: chunking strategies, hybrid search, reranker |
| Evals + traçabilitat | Suite d'evals amb mètriques de retrieval i de resposta; Langfuse per traça |
| Prompt engineering | Structured output obligatori (Pydantic), few-shot per citacions |
| Python com a llenguatge principal | Async, Pydantic v2, mypy strict, ruff — el teu estàndard de sempre |

**Per què "codi propi" i no documents genèrics:** és un corpus que ja tens, amb preguntes
que de veritat et fas, i et obliga a resoldre els problemes durs del RAG sobre codi
(chunking de fitxers llargs, respectar estructures, citations exactes a fitxer+línia).
A més, és demostrable en una entrevista sense NDA ni dades fictícies.

---

## 2. Alcance funcional (MVP)

1. **Ingesta**: CLI que indexa un repo local — fitxers `.md`, `.py`, `.toml`, `.yaml` —
   filtrant per `.gitignore`. Guarda chunk, embedding, metadades (path, línies, hash, llenguatge).
2. **Consulta**: pregunta en llenguatge natural → resposta amb **citacions**
   (`path:linia_inici-linia_fi`) i un veredicte de confiança. Resposta **estructurada**
   (Pydantic), mai text lliure sense validar.
3. **Eval contínua**: dataset daurat de ~40 parells pregunta/resposta-esperada sobre
   els teus repos; cada canvi de chunker/embedder/prompt es mesura, no s'estima.
4. **Traçabilitat**: cada query genera una traça a Langfuse (retrieval, rerank, prompt, resposta, cost, latència).

**Fora d'abast (MVP):** UI web, multi-tenant, indexació incremental en temps real, indexació d'issues/PRs remotes.

---

## 3. Arquitectura

```
                        ┌─────────────────────────────────────────┐
  repo local ──ingest──▶│ READERS → CHUNKERS → EMBEDDER → STORE   │
                        └─────────────────────────────────────────┘
                                          │ pgvector (default) / Qdrant (adapter)
                                          ▼
  pregunta ──▶ FastAPI ──▶ RETRIEVER (dense + BM25 → RRF) ──▶ RERANKER ──▶ PROMPT ──▶ LLM
                                          │                                 │
                                          └────────── Langfuse ◀── traça ◀──┘
                                          ▼
                              Eval harness (pytest + judge)
```

Principis que aplicaràs del teu estil de treball:

- **I/O als bordes**: readers, embedders, stores i LLM són ports (protocols); el core
  (chunking decisions, fusion RRF, muntatge de prompt) és lògica pura i testeja sense xarxa.
- **Adapters per intercambiabilitat**: `VectorStore`, `Embedder`, `LlmClient` com a
  `Protocol` → pgvector i Qdrant intercanviables sense tocar el core.
- **Eval-first**: abans de canviar qualsevol component, l'eval corre en vermell sobre el baseline.

---

## 4. Decisions tècniques a prendre (i documentar com a ADR)

Aquestes decisions **són el contingut tècnic del projecte** — cada una amb experiment + mètrica + ADR curt:

1. **Chunking**: què funciona millor sobre codi? Fixed-size vs recursive vs *per símbol*
   (funció/classe via AST de Python, encapçalaments de Markdown). Mideu **recall@5** i
   **nDCG** sobre el dataset daurat.
2. **Embeddings**: model local (Ollama `nomic-embed-text`, ja el pots servir amb els teus GGUF)
   vs API (`text-embedding-3-small`). Cost per indexació completa vs qualitat.
3. **Store**: pgvector vs Qdrant — mateixa suite d'evals, mateix corpus; compares latència p95,
   facilitat de filtres per metadades, i operativa (ja saps SQL; Compose fa la resta).
4. **Hybrid search**: BM25 (Postgres FTS o `tantivy-py`) + dense amb Reciprocal Rank Fusion.
   Mesura: quant guanya hybrid vs dense sola en recall@5?
5. **Reranking**: cross-encoder local (`bge-reranker-base` via sentence-transformers) com a
   segona fase sobre top-20 → top-5. Mesura cost de latència vs guany de precisió.
6. **Prompt de generació**: few-shot amb 2-3 exemples de resposta ben citada vs zero-shot;
   structured output amb `llm.with_structured_output(Pydantic)` o `instructor`.

---

## 5. Evals (el cor del projecte)

**Dataset daurat** (`evals/golden/*.yaml`): ~40 entrades, cada una amb:
`question`, `expected_files` (paths que han de sortir al retrieval), `answer_contains`
(fets que la resposta ha de mencionar), `repo` (etiqueta).

**Tres capes de mètrica:**

| Capa | Mètrica | Eina |
|---|---|---|
| Retrieval | recall@5, MRR, nDCG | propi, pytest — determinista, sense LLM |
| Fidelitat | la resposta cita fitxers reals? al·lucina paths? | assertions deterministes + judge |
| Qualitat | answer correctness vs `answer_contains` | LLM-as-judge (model fort, mateix criteri sempre) |

**Regles:**
- Les evals de retrieval i citacions corren a **CI en cada PR** (deterministes, ràpides).
- Les del judge corren **manual/nightly** (cost). Resultats publicats com a artefacte:
  una taula markdown amb el score de la versió actual vs baseline.
- **Cap canvi de chunker/embedder/prompt es mergea si baixa el recall@5** sense un ADR que ho justifiqui.
  Això és exactament el discurs "evals = tests per a prompts" que diferencia en una entrevista.

---

## 6. Stack

| Capa | Elecció | Nota |
|---|---|---|
| Llenguatge | Python 3.13, mypy strict, ruff | el teu estàndard (`md-mermaid-pdf` ja ho fa) |
| API | FastAPI + uvicorn | `/query`, `/ingest`, `/health` |
| CLI | typer | ingest + query des de terminal |
| Vector store | pgvector (default), adapter Qdrant | Postgres + pgvector en Compose |
| BM25 | `tantivy-py` o FTS de Postgres | per hybrid |
| Embeddings | Ollama local + `text-embedding-3-small` (adapter) | trade-off cost/qualitat documentat |
| Reranker | `sentence-transformers` (bge-reranker-base) | opcional, activable per config |
| LLM | `litellm` o adapters propis (Anthropic + Ollama) | no lock-in |
| Observabilitat | Langfuse (self-hosted al Compose) | traça per query amb cost i latència |
| Test | pytest + `pytest-asyncio` | evals com a tests, markers `@pytest.mark.eval` |
| CI | GitHub Actions | lint + mypy + tests + evals deterministes |

---

## 7. Estructura de repositori inicial

```
codebase-rag/
├── pyproject.toml
├── docker-compose.yml          # app + postgres/pgvector + langfuse (+ qdrant perfil)
├── src/coderag/
│   ├── ingest/                 # readers, chunkers (fix, recursive, ast), pipeline
│   ├── retrieval/              # dense, bm25, fusion (rrf), reranker
│   ├── generation/             # prompt builder, structured output, citations
│   ├── stores/                 # protocols + pgvector + qdrant adapters
│   ├── llm/                    # adapters providers (ollama, anthropic, openai)
│   ├── api/                    # FastAPI
│   └── cli.py                  # typer: ingest / query / eval
├── evals/
│   ├── golden/                 # dataset daurat (yaml, versionat)
│   ├── harness.py              # execució + càlcul mètriques
│   └── reports/                # resultats versionats per run (md)
├── adr/                        # ADR-001 chunking, ADR-002 embeddings, ...
├── tests/                      # unitaris (core pur), integració (compose)
└── README.md                   # amb taula de mètriques baseline vs actual
```

---

## 8. Fases

| Fase | Entregable | Criteri de fet |
|---|---|---|
| 0. Setup | repo, CI vermella-verda, mypy strict, ruff | CI en verd amb 1 test trivial |
| 1. Ingesta + pgvector | CLI `ingest` + `query` naive (dense, top-5, resposta lliure) | indexa un repo real sencer en < 2 min |
| 2. Eval harness | dataset daurat v1 + mètriques retrieval | baseline recall@5 documentat al README |
| 3. Hybrid + rerank | BM25+RRF i reranker activables | experiment amb taula: dense vs hybrid vs hybrid+rerank |
| 4. Generació estructurada | resposta Pydantic amb citacions exactes | 0 citacions a paths inexistents sobre el dataset |
| 5. Observabilitat | Langfuse amb traça completa per query | cada query té traça amb cost i latència |
| 6. Qdrant adapter | segon store, mateixa suite | taula comparativa pgvector vs Qdrant a l'ADR |
| 7. API + Compose | FastAPI + docker compose up | demo end-to-end des de zero en 1 comandament |

**Estimació honesta:** 4-6 setmanes a temps parcial. Les fases 2-4 són les que valen
or en una entrevista — no les salteu per arribar abans a la UI (que no hi ha, i està bé).

---

## 9. Com presentar-lo

- **README amb la taula de mètriques** (baseline vs millores per experiment) — això és
  el que distingeix "he fet un RAG" de "sé dirigir un RAG amb dades".
- Els **ADRs curts** (mitja pàgina cada un) demostren raonament de trade-offs, el requisit
  més sènior de l'oferta.
- A l'entrevista: "les evals em van dir que el reranker només valia la pena per sobre de
  X grandària de corpus" val més que qualsevol llista de tecnologies.

## 10. Riscos i plan B

- **Cost d'API d'embeddings/LLM en evals repetides** → embedder local per defecte; judge només nightly.
- **Dataset daurat fluix** → comença amb 15 preguntes bones sobre 1 repo, creix-lo quan detectis falles reals.
- **Langfuse self-hosted pesat** → alternativa mínima: logs estructurats JSONL + taula de runs; migra després.
