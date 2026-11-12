# What codebaserag does (plain-language overview)

This page explains the tool to readers who have never worked with a RAG system.
No prior knowledge assumed; every term is defined the first time it appears.
If you already know the territory, the [README](../README.md) and
[architecture.md](architecture.md) are the fast paths.

## The problem

You have a repository with thousands of files and a question: *how does
authentication work?*, *where are the AI models configured?*, *why does this
function do that?*

Without help there are two options: search through files by hand (slow, and you
can miss the file that matters), or ask a general-purpose AI such as ChatGPT.
The second option is dangerous: **the model does not know your code**, so either
you paste fragments out of your machine (costly, and your code leaves your
machine) or it invents an answer with a confident tone. Nobody can build on an
invented answer.

## What codebaserag is

codebaserag lets you ask questions about your own repository in plain language
and answers **with real references**: the file, the lines, the exact fragment
the answer is built from. Answer and evidence together, every time.

In one sentence: *a librarian who knows your entire codebase, finds the right
passage in seconds, and cites it.*

## How it works, piece by piece

The core idea is **RAG** (*Retrieval-Augmented Generation*, "retrieval augmented
generation"): instead of letting the model invent the answer, it first
**retrieves** the relevant code fragments and then **writes** the answer on top
of them — like a student who opens the book and finds the right chapter before
responding.

Four phases:

### 1. Reading and preparation (ingest)

The tool walks the repository honouring `.gitignore` (it never indexes what you
have told it is junk), reads only the file types it understands (Python,
Markdown, YAML, TOML), and splits every file into 40-line windows. Each window
gets a *hash* — a fingerprint that makes it identifiable. It is like
photocopying the book page by page and labelling every snippet.

### 2. Memory (embedder and vector store)

This is the part that sounds scary, and it is simpler than it looks. To find
"relevant" fragments you have to measure relevance, and to measure it you have
to turn text into numbers. The **embedder** does exactly that: it converts each
snippet into a list of numbers (a *vector*). The trick is that snippets about
the same topic end up with **similar** numbers. "how authentication works" and
"session verification" land close together; "compilation" lands far away. It is
a map: meaning becomes distance.

Vectors are stored in a **vector store** (a database that answers "give me the
five snippets closest to this point"). codebaserag ships four behind the same
connector: *memory* (in RAM, for experiments), *pgvector* and *Qdrant*
(persistent, for production) and *LlamaIndex* (a different ecosystem, same
connector).

### 3. Search (the retriever)

When you ask, the tool runs three things at once:

- **Semantic search**: embed the query and ask for the closest snippets.
  Perfect for meaning, blind to exact wording.
- **Lexical search (BM25)**: the classic word-matching algorithm behind web
  search. Finds exact terms ("Langfuse", "pgvector") but understands no
  synonyms.
- **Fusion (RRF)**: blends the two lists. A snippet that ranks well in both
  goes up. The principle: two independent systems fail in different ways; when
  they agree, they are usually right.

There is also an optional **rerank** step: a small model that re-reads the top
20 candidates and reorders them with judgement — like an editor receiving
drafts and sorting them by importance.

### 4. Answer (the generator)

With the fragments in hand, an LLM writes the answer **forced to cite** its
sources. If the answer says "the nodes are defined in `graph.py:41`", it is
because that fragment was among the retrieved ones. If the evidence is not
there, it says so instead of guessing.

## Choosing a store: pgvector vs Qdrant vs LlamaIndex

All stores sit behind the same `VectorStore` port, so `--store` swaps without
touching a line of the core — and the eval gate is the same for all of them.
They differ in what they *are*:

| | pgvector | Qdrant | LlamaIndex |
|---|---|---|---|
| What it is | an extension of PostgreSQL | a dedicated vector database (Rust) | a RAG framework (Python library) |
| Where vectors live | in your existing Postgres, next to your app data | in its own server / collection | in process memory (`SimpleVectorStore`) |
| Persistence | yes, with the rest of your data | yes | no — rebuilt on every run |
| Extra infrastructure | none beyond Postgres | one more service to run | none (optional dependency) |
| Pairing in codebaserag | BM25 on the same Postgres (FTS) | BM25 on Postgres FTS or Tantivy | BM25 in memory |
| Embedder | real (Ollama / llama.cpp) after `coderag ingest` | real after `coderag ingest` | deterministic `HashEmbedder` (offline) |

In plain terms:

- **pgvector** is the default: vectors live *inside* the database you probably
  already run. One system to back up, monitor and query, and SQL joins with the
  rest of your data. The choice for most teams.
- **Qdrant** is a purpose-built vector database: the fastest path when you need
  heavy filtering, very large corpora or high query rates, and you are happy to
  operate a dedicated service.
- **LlamaIndex** is a different kind of thing: not a database but a whole RAG
  ecosystem (nodes, indices, query engines). codebaserag's backend runs its
  in-memory `SimpleVectorStore` over our own corpus and embedder — a
  portability proof with score parity against the in-memory store, not a
  production store. Experiment there; persist with pgvector or Qdrant.

## Why you can trust it

This is where codebaserag differs from a weekend demo: it ships an automatic
**evaluation harness**.

- A **golden set**: 44 questions with known answers over this repository
  (*"how are source files discovered?" → `ingest/readers.py`*).
- **Metrics**: recall (did it find the right file?), MRR (at which position?)
  and nDCG (did the most relevant come first?).
- A **baseline**: the minimum score below which the pipeline does not ship —
  the same idea as a unit test, but for answer quality.

All of it runs in CI on every push: formatting, lint, strict type checks and
tests. This is a project with gates, not a demo.

## What it is not

- **Not a coding copilot**: it does not write or edit code. It reads, searches
  and explains.
- **It does not invent**: if the evidence is not there, it says so. That is the
  whole point.
- **It does not send your code anywhere** when run locally: the embedder and
  the model can run on your own machine (Ollama, llama.cpp).

## In one line

> Ask your repository a question in normal words; codebaserag finds the relevant
> code fragments, answers, and tells you exactly which file and lines the
> answer comes from — with an automatic test that guarantees it does not
> regress.

## See it

- [Architecture diagram](https://jordimarsal.github.io/codebaserag/diagrams/architecture.html): components, ports and the eval harness.
- [Query sequence diagram](https://jordimarsal.github.io/codebaserag/diagrams/query-sequence.html): one hybrid query, step by step.
- [README quick start](../README.md): install, commands and the eval baseline.
