"""
RAG Tool — FAISS vector store for patient summaries and medical knowledge.
Uses HuggingFace sentence-transformers for embeddings (no API key required).
"""
import json, os, sys, time
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from utils.logger import log_tool_call

_vectorstore = None
_embeddings  = None


def _get_embeddings():
    """Return HuggingFace embeddings, or a lightweight mock if libraries unavailable."""
    global _embeddings
    if _embeddings is not None:
        return _embeddings
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
        _embeddings = HuggingFaceEmbeddings(
            model_name=config.EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
    except Exception:
        # Fallback: simple TF-IDF-style mock embeddings (no API key or GPU needed)
        from langchain.embeddings.base import Embeddings
        import hashlib, numpy as np

        class _MockEmbeddings(Embeddings):
            """Deterministic hash-based mock embeddings for demo use."""
            def _embed(self, text: str):
                h = hashlib.sha256(text.encode()).digest()
                vec = np.frombuffer(h, dtype=np.uint8).astype(float)
                vec = vec / (np.linalg.norm(vec) + 1e-9)
                return vec.tolist()

            def embed_documents(self, texts):
                return [self._embed(t) for t in texts]

            def embed_query(self, text: str):
                return self._embed(text)

        _embeddings = _MockEmbeddings()
    return _embeddings


def _get_or_create_vs():
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    from langchain_community.vectorstores import FAISS
    from langchain.schema import Document

    index_path = os.path.join(config.VECTORSTORE_DIR, "patient_index")
    emb = _get_embeddings()

    if os.path.exists(index_path):
        try:
            _vectorstore = FAISS.load_local(
                index_path, emb, allow_dangerous_deserialization=True)
            return _vectorstore
        except Exception:
            pass

    docs = _build_docs()
    if not docs:
        docs = [Document(page_content="Healthcare assistant initialised.",
                         metadata={"type": "system"})]
    _vectorstore = FAISS.from_documents(docs, emb)
    _vectorstore.save_local(index_path)
    return _vectorstore


def _build_docs() -> List:
    from langchain.schema import Document
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    with open(config.PATIENTS_FILE) as f:
        patients = json.load(f)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)
    docs = []
    for p in patients:
        text = (f"Patient: {p['name']} (ID: {p['patient_id']})\n"
                f"Age: {p['age']}, Gender: {p['gender']}, "
                f"Blood Group: {p['blood_group']}\n"
                f"Allergies: {', '.join(p.get('allergies',['None']))}\n"
                f"Medications: {', '.join(p.get('current_medications',[]))}\n\n"
                "Medical History:\n")
        for e in p.get("medical_history", []):
            text += (f"  [{e['date']}] {e['diagnosis']}\n"
                     f"  Treatment: {e['treatment']}\n"
                     f"  Notes: {e['notes']}\n\n")
        for chunk in splitter.split_text(text):
            docs.append(Document(page_content=chunk,
                                 metadata={"patient_id": p["patient_id"],
                                           "patient_name": p["name"],
                                           "type": "patient_record"}))
    return docs


# ── Public API ────────────────────────────────────────────────────────────────

def retrieve_patient_context(query: str,
                              patient_id: Optional[str] = None) -> Dict[str, Any]:
    """Semantic search over patient records."""
    start = time.time()
    try:
        vs   = _get_or_create_vs()
        docs = vs.similarity_search(query, k=config.TOP_K_RESULTS)
        if patient_id:
            filtered = [d for d in docs if d.metadata.get("patient_id") == patient_id]
            docs = filtered if filtered else docs

        context = "\n\n---\n\n".join(d.page_content for d in docs)
        result  = {"success": True, "query": query, "context": context,
                   "sources": [d.metadata for d in docs],
                   "chunks_retrieved": len(docs)}
        log_tool_call("retrieve_patient_context", query, f"{len(docs)} chunks", True,
                      duration_ms=(time.time()-start)*1000, patient_id=patient_id)
        return result
    except Exception as e:
        log_tool_call("retrieve_patient_context", query, str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}


def rebuild_vectorstore() -> Dict[str, Any]:
    """Force re-index all patient documents."""
    global _vectorstore
    start = time.time()
    try:
        from langchain_community.vectorstores import FAISS
        index_path = os.path.join(config.VECTORSTORE_DIR, "patient_index")
        docs  = _build_docs()
        emb   = _get_embeddings()
        _vectorstore = FAISS.from_documents(docs, emb)
        _vectorstore.save_local(index_path)
        result = {"success": True,
                  "message": f"Vector store rebuilt with {len(docs)} chunks.",
                  "documents_indexed": len(docs)}
        log_tool_call("rebuild_vectorstore", "full", result, True,
                      duration_ms=(time.time()-start)*1000)
        return result
    except Exception as e:
        log_tool_call("rebuild_vectorstore", "full", str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}


def add_document_to_store(text: str, metadata: Dict) -> Dict[str, Any]:
    start = time.time()
    try:
        from langchain.schema import Document
        vs  = _get_or_create_vs()
        doc = Document(page_content=text, metadata=metadata)
        vs.add_documents([doc])
        vs.save_local(os.path.join(config.VECTORSTORE_DIR, "patient_index"))
        result = {"success": True, "message": "Document added to vector store."}
        log_tool_call("add_document_to_store", text[:80], result, True,
                      duration_ms=(time.time()-start)*1000)
        return result
    except Exception as e:
        log_tool_call("add_document_to_store", text[:80], str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e)}
