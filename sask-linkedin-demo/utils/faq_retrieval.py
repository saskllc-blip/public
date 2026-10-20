"""FAQ retrieval and matching."""

from typing import List
from fixtures.faq import FAQ_CONTENT


def retrieve_faq(query: str, top_k: int = 3) -> List[str]:
    """
    Retrieve relevant FAQ sections based on keyword matching.

    Args:
        query: User question
        top_k: Maximum number of results

    Returns:
        List of FAQ sections matching the query
    """
    if not query or not isinstance(query, str):
        return []

    query_lower = query.lower()
    results = []

    # Split FAQ into Q&A sections
    sections = FAQ_CONTENT.split("\n\n")

    for section in sections:
        if "**Q:" in section and "**A:" in section:
            # Simple keyword matching
            if any(keyword in section.lower() for keyword in query_lower.split()):
                results.append(section)

    # Return top_k results
    return results[:top_k]
