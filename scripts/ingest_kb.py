"""
Build the vector index from the knowledge_base/*.md files.
Run once before starting the API:  python scripts/ingest_kb.py
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + "/.."))

from app.rag import build_index

if __name__ == "__main__":
    n = build_index("knowledge_base")
    print(f"Indexed {n} chunks into the vector store.")
