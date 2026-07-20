"""
Central configuration.

Why a separate config file? So model names, limits, and knobs live in ONE place.
On an interview you can say: "I isolated configuration so swapping models or tuning
limits doesn't touch business logic." That is a small but real engineering signal.
"""

# Model IDs. Verify the current names at https://docs.claude.com/en/docs/about-claude/models
# We use a strong model for reasoning-heavy steps and a cheaper/faster one where quality
# is less critical. Choosing the model per-step is a basic cost-control technique.
MODEL_SMART = "claude-sonnet-5"          # analysis, research, final evaluation
MODEL_FAST = "claude-haiku-4-5-20251001"  # cheap steps (not heavily used here)

# Generation limits
MAX_TOKENS = 1500

# How many times the research step is allowed to call the web-search tool.
# Bounding tool loops prevents runaway cost / infinite loops.
MAX_SEARCH_ITERATIONS = 3

# Retry policy for transient API errors (network blips, rate limits, overload).
MAX_RETRIES = 4
RETRY_BASE_DELAY = 1.0  # seconds; grows exponentially: 1, 2, 4, 8 ...

# RAG
CHROMA_DIR = "chroma_store"       # where the local vector DB is persisted
KB_COLLECTION = "startup_knowledge"
RAG_TOP_K = 3                     # how many knowledge chunks to retrieve
