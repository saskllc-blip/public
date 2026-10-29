"""
langchain 1.x removed the `langchain.schema` and `langchain.text_splitter`
shims, and requirements.txt only sets a floor (langchain>=0.2.0), so a fresh
install gets 1.x. These tests hide the legacy modules to prove the RAG index
and the LLM call path import only from locations that exist in both lines.
"""
import sys
from types import SimpleNamespace

import pytest

from agents import healthcare_agent
from tools import rag_tool

LEGACY = ["langchain.schema", "langchain.text_splitter", "langchain.embeddings.base"]


@pytest.fixture
def langchain_1x(monkeypatch):
    for mod in LEGACY:
        monkeypatch.setitem(sys.modules, mod, None)  # import now raises ImportError


def test_rag_builds_docs_without_legacy_langchain(langchain_1x):
    docs = rag_tool._build_docs()
    assert docs and all(d.metadata.get("patient_id") for d in docs)


def test_rebuild_vectorstore_without_legacy_langchain(langchain_1x, tmp_path, monkeypatch):
    import config
    monkeypatch.setattr(config, "VECTORSTORE_DIR", str(tmp_path))
    monkeypatch.setattr(rag_tool, "_vectorstore", None)
    r = rag_tool.rebuild_vectorstore()
    assert r["success"], r.get("error")


def test_llm_call_without_legacy_langchain(langchain_1x, monkeypatch):
    fake = SimpleNamespace(invoke=lambda msgs: SimpleNamespace(content="synthesised answer"))
    monkeypatch.setattr(healthcare_agent, "_get_llm", lambda: fake)
    assert healthcare_agent._llm_call("prompt") == "synthesised answer"
