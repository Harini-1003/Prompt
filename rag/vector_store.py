import json
import sqlite3
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from config import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL_NAME, DATA_DIR
from ingestion.structure_extractor import extract_units

# Persistent local vector storage directory
VECTOR_STORE_DIR = DATA_DIR / "vector_indices"
VECTOR_STORE_DIR.mkdir(exist_ok=True)

class EmbeddingService:
    _instance = None
    _model = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
            self._model = SentenceTransformer(EMBEDDING_MODEL_NAME)
            print("Embedding model loaded successfully!")
        except Exception as e:
            print(f"Warning: Failed to load SentenceTransformer ({e}). Falling back to dummy embeddings.")
            self._model = None

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        if self._model is not None and texts:
            embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            # Normalize embeddings for cosine similarity
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return embeddings / norms
        # Fallback dummy 384-dim vector
        return np.zeros((len(texts), 384), dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        if self._model is not None:
            emb = self._model.encode([query], convert_to_numpy=True, show_progress_bar=False)[0]
            norm = np.linalg.norm(emb)
            return emb / (norm if norm != 0 else 1.0)
        return np.zeros(384, dtype=np.float32)

def chunk_text_with_metadata(
    full_text: str,
    subject_id: int,
    subject_name: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Split text into chunks of approx 500-800 words/tokens with overlap,
    annotated with unit, topic, subject_id, and chunk index metadata.
    """
    units = extract_units(full_text)
    all_chunks = []
    chunk_counter = 0

    for u_idx, u in enumerate(units):
        unit_name = u["unit"]
        unit_title = u["title"]
        content = u["content"]

        # Tokenize by words
        words = content.split()
        if not words:
            continue

        step = max(1, chunk_size - chunk_overlap)
        for i in range(0, len(words), step):
            chunk_words = words[i : i + chunk_size]
            chunk_text = " ".join(chunk_words)
            if len(chunk_words) < 20 and all_chunks:
                # Merge tiny trailing fragments into previous chunk
                all_chunks[-1]["text"] += " " + chunk_text
                continue

            chunk_counter += 1
            all_chunks.append({
                "chunk_id": f"subj_{subject_id}_chk_{chunk_counter}",
                "subject_id": subject_id,
                "subject_name": subject_name,
                "unit": unit_name,
                "topic": unit_title,
                "text": chunk_text,
                "token_estimate": len(chunk_words)
            })

    return all_chunks

class SubjectVectorIndex:
    """
    Separate, dedicated vector store for each subject using FAISS or high-performance numpy cosine retrieval.
    Keeps subject syllabi completely isolated.
    """
    def __init__(self, subject_id: int):
        self.subject_id = subject_id
        self.index_file = VECTOR_STORE_DIR / f"subject_{subject_id}_index.json"
        self.vectors_file = VECTOR_STORE_DIR / f"subject_{subject_id}_vectors.npy"
        self.chunks: List[Dict[str, Any]] = []
        self.embeddings: Optional[np.ndarray] = None
        self.load()

    def load(self):
        if self.index_file.exists() and self.vectors_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.chunks = json.load(f)
                self.embeddings = np.load(str(self.vectors_file))
            except Exception as e:
                print(f"Error loading index for subject {self.subject_id}: {e}")
                self.chunks = []
                self.embeddings = None

    def save(self):
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(self.chunks, f, ensure_ascii=False, indent=2)
        if self.embeddings is not None:
            np.save(str(self.vectors_file), self.embeddings)

    def build_index(self, chunks: List[Dict[str, Any]]):
        if not chunks:
            self.chunks = []
            self.embeddings = None
            self.save()
            return

        self.chunks = chunks
        texts = [c["text"] for c in chunks]
        service = EmbeddingService.get_instance()
        self.embeddings = service.embed_documents(texts)
        self.save()

    def search(self, query: str, top_k: int = 4, unit_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.chunks or self.embeddings is None:
            return []

        service = EmbeddingService.get_instance()
        query_vec = service.embed_query(query)

        # Compute cosine similarities
        scores = np.dot(self.embeddings, query_vec)
        
        # Apply optional unit filtering
        valid_indices = []
        for i, chk in enumerate(self.chunks):
            if unit_filter and unit_filter.lower() not in chk.get("unit", "").lower():
                continue
            valid_indices.append(i)

        if not valid_indices:
            valid_indices = list(range(len(self.chunks)))

        filtered_scores = scores[valid_indices]
        top_sub_indices = np.argsort(filtered_scores)[::-1][:top_k]

        results = []
        for sub_idx in top_sub_indices:
            idx = valid_indices[sub_idx]
            chk = dict(self.chunks[idx])
            chk["similarity_score"] = float(scores[idx])
            results.append(chk)

        return results
