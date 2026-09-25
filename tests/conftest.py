"""Shared pytest config: skip adapter tests when optional extras are absent."""

collect_ignore = []

try:
    import psycopg  # noqa: F401  (pgvector extra)
except ImportError:
    collect_ignore.append("test_pgvector.py")
