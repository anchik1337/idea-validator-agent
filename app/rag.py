"""
Retrieval-Augmented Generation (RAG).

Why RAG here instead of stuffing everything into the prompt or fine-tuning?
  - Fine-tuning is expensive, slow, and overkill for a small, changing knowledge base.
  - RAG lets us update the knowledge base by editing markdown files, no retraining.
  - We only inject the few most relevant chunks, which saves tokens and improves focus.
That three-line answer is a very common interview question ("RAG vs fine-tuning?").

We use ChromaDB with its built-in local embedding model, so it works offline
after the first run and needs no extra API key.
"""

import os
import glob
import chromadb

from .config import CHROMA_DIR, KB_COLLECTION, RAG_TOP_K


def _client():
    return chromadb.PersistentClient(path=CHROMA_DIR)


def build_index(kb_dir: str = "knowledge_base") -> int:
    """
    Read every .md file in kb_dir, split into chunks, embed, and store in Chroma.
    Returns the number of chunks indexed. Run this once via scripts/ingest_kb.py.
    """
    client = _client()
    # Reset the collection so re-running gives a clean index.
    try:
        client.delete_collection(KB_COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(KB_COLLECTION)

    docs, ids, metas = [], [], []
    for path in glob.glob(os.path.join(kb_dir, "*.md")):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        # Simple chunking: split on blank lines into paragraphs.
        # Chunking strategy matters in RAG; we keep it simple and explainable.
        chunks = [c.strip() for c in text.split("\n\n") if len(c.strip()) > 40]
        fname = os.path.basename(path)
        for i, chunk in enumerate(chunks):
            docs.append(chunk)
            ids.append(f"{fname}-{i}")
            metas.append({"source": fname})

    if docs:
        collection.add(documents=docs, ids=ids, metadatas=metas)
    return len(docs)


def retrieve(query: str, k: int = RAG_TOP_K) -> list[str]:
    """Return the k most relevant knowledge chunks for `query`."""
    client = _client()
    try:
        collection = client.get_collection(KB_COLLECTION)
    except Exception:
        # If the index was never built, degrade gracefully.
        return []
    res = collection.query(query_texts=[query], n_results=k)
    return res.get("documents", [[]])[0]
