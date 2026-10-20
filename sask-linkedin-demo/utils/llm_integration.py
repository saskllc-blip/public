"""LLM integration for chatbot responses."""

from typing import List


# Fallback responses when LLM unavailable
FALLBACK_RESPONSES = [
    "I'm here to help with property management questions. Please ask about tenant screening, lease terms, maintenance, rent, or security deposits.",
    "Great question! Based on SASK LLC's property management practices, I recommend contacting your property manager for specific details.",
    "That's an important topic. SASK LLC prioritizes compliance and transparency in all property management matters.",
    "I appreciate your question. For the most accurate information, please refer to your lease agreement or contact our team.",
]


def generate_chatbot_response(
    user_query: str,
    faq_context: List[str],
    use_fallback: bool = False,
) -> str:
    """
    Generate chatbot response based on FAQ context.

    Args:
        user_query: User's question
        faq_context: Retrieved FAQ sections
        use_fallback: Use fallback response if LLM unavailable

    Returns:
        Chatbot response (50-500 characters)
    """
    if not user_query:
        return "I'm ready to help! Ask me about tenant screening, leases, maintenance, or rent collection."

    # In production, this would call Claude, GPT, Ollama, etc.
    # For now, return a grounded mock response

    if use_fallback or not faq_context:
        return FALLBACK_RESPONSES[
            hash(user_query) % len(FALLBACK_RESPONSES)
        ]

    # Build a simple response grounded in FAQ
    faq_text = " ".join(faq_context)[:300]

    responses = {
        "tenant": "Tenant screening is an important part of our process. We verify background, credit, and employment to ensure the best possible matches between properties and tenants.",
        "rent": "Rent is due on the 1st of each month. We accept ACH transfer, check, and credit card payments via our online portal. Late fees apply after the 5th.",
        "maintenance": "To request maintenance, submit a request via our online portal or call your property manager. Emergency repairs are prioritized for same-day response.",
        "lease": "Our standard leases are 12-month terms. Rent increases only take effect at lease renewal with 60 days' notice.",
        "security": "Security deposits are held in a separate account and returned within 30 days of lease end, minus deductions for damages beyond normal wear.",
    }

    # Return response based on query keyword
    for keyword, response in responses.items():
        if keyword in user_query.lower():
            return response

    # Default response grounded in FAQ
    return (
        "Thank you for your question. At SASK LLC, we believe in transparency and compliance in all "
        "property management practices. For specific details about your property, please contact your property manager."
    )
