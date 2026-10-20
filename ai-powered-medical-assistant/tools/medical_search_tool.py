"""
Medical Search Tool — fetches disease/treatment information from Wikipedia
with DuckDuckGo (Medline/WHO-filtered) as fallback.
"""
import os, sys, time
from typing import Any, Dict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import log_tool_call


def search_medical_info(query: str) -> Dict[str, Any]:
    """Primary search via Wikipedia; falls back to DuckDuckGo if no page found."""
    start = time.time()
    try:
        import wikipedia
        wikipedia.set_lang("en")
        try:
            summary = wikipedia.summary(query, sentences=6, auto_suggest=True)
            page    = wikipedia.page(query, auto_suggest=True)
            result  = {"success": True, "source": "Wikipedia",
                       "title": page.title, "url": page.url,
                       "summary": summary, "query": query}
        except wikipedia.exceptions.DisambiguationError as de:
            opt     = de.options[0]
            summary = wikipedia.summary(opt, sentences=6)
            result  = {"success": True, "source": "Wikipedia (disambiguated)",
                       "title": opt, "url": "", "summary": summary, "query": query,
                       "note": f"Options: {de.options[:5]}"}
        except wikipedia.exceptions.PageError:
            result = _ddg_fallback(query)

        log_tool_call("search_medical_info", query,
                      result.get("summary","")[:200], True,
                      duration_ms=(time.time()-start)*1000)
        return result
    except Exception as e:
        log_tool_call("search_medical_info", query, str(e), False,
                      error=str(e), duration_ms=(time.time()-start)*1000)
        return {"success": False, "error": str(e), "query": query}


def _ddg_fallback(query: str) -> Dict[str, Any]:
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(
                f"medical information {query} site:medlineplus.gov OR site:who.int OR site:nih.gov",
                max_results=3))
        if results:
            combined = "\n\n".join(f"{r['title']}: {r['body']}" for r in results[:3])
            return {"success": True, "source": "DuckDuckGo (Medline/WHO)",
                    "title": query, "url": results[0].get("href",""),
                    "summary": combined, "query": query}
        return {"success": False, "source": "DuckDuckGo",
                "error": "No results found.", "query": query}
    except Exception as e:
        return {"success": False, "error": str(e), "query": query}


def search_drug_info(drug_name: str) -> Dict[str, Any]:
    return search_medical_info(f"{drug_name} medication uses side effects dosage")

def search_treatment_options(disease: str) -> Dict[str, Any]:
    return search_medical_info(f"{disease} treatment options latest methods clinical guidelines")
