"""Vector store with Qdrant. Per-session collections."""

from __future__ import annotations

from typing import List, Optional

from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from src.config import settings


class SessionVectorStore:
    """Per-session vector index backed by Qdrant Cloud."""

    def __init__(self) -> None:
        self._qdrant: Optional[QdrantClient] = None
        self._init_qdrant()

    def _init_qdrant(self) -> None:
        if not settings.qdrant_url or settings.qdrant_url == "http://localhost:6333":
            print("[VectorStore] QDRANT_URL not set, vector store disabled")
            return
        try:
            kwargs = {
                "url": settings.qdrant_url,
                "timeout": 30,
                "check_compatibility": False,
            }
            if settings.qdrant_api_key:
                kwargs["api_key"] = settings.qdrant_api_key
            self._qdrant = QdrantClient(**kwargs)
            self._qdrant.get_collections()
            print("[VectorStore] Qdrant connected")
        except Exception as e:
            print(f"[VectorStore] Qdrant connection failed: {e}")
            self._qdrant = None

    def index_documents(self, session_id: str, texts: List[str]) -> int:
        if not texts:
            return 0
        if self._qdrant is None:
            print("[VectorStore] Qdrant not available, skipping indexing")
            return 0
        try:
            return self._index_qdrant(session_id, texts)
        except Exception as e:
            print(f"[VectorStore] Qdrant index failed: {e}")
            return 0

    def _get_embed_model(self):
        if "localhost:11434" in settings.openai_base_url or "127.0.0.1:11434" in settings.openai_base_url:
            return OllamaEmbedding(
                model_name="nomic-embed-text",
                base_url=settings.openai_base_url.replace("/v1", ""),
            )
        return OpenAIEmbedding(
            api_key=settings.openai_api_key or "dummy",
            api_base=settings.openai_base_url,
            model="text-embedding-3-small",
        )

    def _index_qdrant(self, session_id: str, texts: List[str]) -> int:
        embed_model = self._get_embed_model()
        Settings.embed_model = embed_model

        vector_store = QdrantVectorStore(
            client=self._qdrant,
            collection_name=f"session_{session_id}",
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        documents = [Document(text=t) for t in texts]
        VectorStoreIndex.from_documents(documents, storage_context=storage_context)
        return len(documents)

    def query(self, session_id: str, query: str, top_k: int = 5) -> List[str]:
        if self._qdrant is None:
            print("[VectorStore] Qdrant not available, returning empty context")
            return []
        try:
            return self._query_qdrant(session_id, query, top_k)
        except Exception as e:
            print(f"[VectorStore] Qdrant query failed: {e}")
            return []

    def _query_qdrant(self, session_id: str, query: str, top_k: int) -> List[str]:
        embed_model = self._get_embed_model()
        Settings.embed_model = embed_model

        vector_store = QdrantVectorStore(
            client=self._qdrant,
            collection_name=f"session_{session_id}",
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex([], storage_context=storage_context)
        retriever = index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)
        return [n.text for n in nodes]

    def delete_session(self, session_id: str) -> None:
        if self._qdrant is not None:
            try:
                self._qdrant.delete_collection(f"session_{session_id}")
            except Exception:
                pass
