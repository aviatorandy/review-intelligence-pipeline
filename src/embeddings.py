"""
Embeds reviews into a ChromaDB collection for semantic search.

Uses Ollama's nomic-embed-text locally (free).
Falls back to sentence-transformers if Ollama embeddings unavailable.
"""
import os
import requests
from pathlib import Path

OLLAMA_EMBED_URL = "http://localhost:11434/api/embeddings"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
CHROMA_DIR = Path("results/chroma")


def _get_chroma_client():
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def embed_text_ollama(text: str) -> list[float]:
    response = requests.post(
        OLLAMA_EMBED_URL,
        json={"model": OLLAMA_EMBED_MODEL, "prompt": text},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["embedding"]


def embed_text_anthropic(text: str) -> list[float]:
    """Use Voyage AI embeddings via Anthropic's recommended partner (free tier)."""
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    # Use sentence-transformers as fallback since Claude doesn't have embeddings API
    raise NotImplementedError("Use sentence-transformers for cloud embeddings")


def embed_text_local(text: str) -> list[float]:
    """Fallback: sentence-transformers (CPU, no Ollama needed)."""
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    return model.encode(text).tolist()


def get_embed_fn():
    """Return the best available embedding function."""
    # Try Ollama first (preferred for local dev)
    try:
        r = requests.post(
            OLLAMA_EMBED_URL,
            json={"model": OLLAMA_EMBED_MODEL, "prompt": "test"},
            timeout=5,
        )
        if r.status_code == 200:
            return embed_text_ollama, "ollama/nomic-embed-text"
    except Exception:
        pass

    # Fall back to sentence-transformers (works everywhere, no API key)
    return embed_text_local, "sentence-transformers/all-MiniLM-L6-v2"


def build_index(job_id: str, rows: list[dict], progress_cb=None) -> str:
    """
    Embed all reviews and store in a ChromaDB collection.
    Returns the collection name.
    """
    import chromadb

    client = _get_chroma_client()
    collection_name = f"reviews_{job_id[:12]}"

    # Delete existing collection if re-indexing
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass

    collection = client.create_collection(
        collection_name,
        metadata={"hnsw:space": "cosine"},
    )

    embed_fn, model_name = get_embed_fn()
    total = len(rows)
    batch_ids = []
    batch_docs = []
    batch_metas = []
    batch_embeddings = []

    BATCH_SIZE = 50

    for i, row in enumerate(rows):
        text = str(row["text"])
        embedding = embed_fn(text)

        batch_ids.append(str(row["review_id"]))
        batch_docs.append(text)
        batch_metas.append({
            "review_id": int(row["review_id"]),
            "label": int(row.get("label", -1)),
            "sentiment": "positive" if int(row.get("label", 1)) == 1 else "negative",
        })
        batch_embeddings.append(embedding)

        if len(batch_ids) >= BATCH_SIZE or i == total - 1:
            collection.add(
                ids=batch_ids,
                documents=batch_docs,
                metadatas=batch_metas,
                embeddings=batch_embeddings,
            )
            batch_ids, batch_docs, batch_metas, batch_embeddings = [], [], [], []

        if progress_cb and i % 10 == 0:
            progress_cb(i + 1, total, model_name)

    return collection_name


def query_index(job_id: str, question: str, n_results: int = 20) -> list[dict]:
    """
    Embed a question and retrieve the most similar reviews.
    Returns list of {review_id, text, sentiment, distance}.
    """
    client = _get_chroma_client()
    collection_name = f"reviews_{job_id[:12]}"

    try:
        collection = client.get_collection(collection_name)
    except Exception:
        return []

    embed_fn, _ = get_embed_fn()
    query_embedding = embed_fn(question)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(n_results, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    rows = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        rows.append({
            "review_id": meta["review_id"],
            "text": doc,
            "sentiment": meta.get("sentiment", "unknown"),
            "relevance": round(1 - dist, 3),
        })

    return rows


def collection_exists(job_id: str) -> bool:
    try:
        client = _get_chroma_client()
        client.get_collection(f"reviews_{job_id[:12]}")
        return True
    except Exception:
        return False
