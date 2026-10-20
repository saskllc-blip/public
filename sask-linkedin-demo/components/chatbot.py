"""AI Chatbot tab component."""

try:
    import streamlit as st
except ImportError:
    st = None

from utils.validators import check_prompt_injection, validate_message
from utils.faq_retrieval import retrieve_faq
from utils.llm_integration import generate_chatbot_response


def render_chatbot_tab():
    """Render AI chatbot tab with FAQ grounding."""
    if st is None:
        return

    st.info(
        "**🤖 AI Chatbot — Demonstration Only**\n\n"
        "This chatbot is trained on a small sample FAQ and may produce "
        "responses that sound authoritative but are fictional. Always verify "
        "with official SASK LLC policies before taking action."
    )

    st.markdown("### Hallucination Guardrails")
    with st.expander("System Limitations", expanded=False):
        st.markdown(
            """
            - Responses are grounded in a fictional FAQ document
            - The chatbot may confabulate details that sound plausible
            - Always verify critical information with official sources
            - This is a demonstration, not a production system
            - API quota: 10 queries per session
            """
        )

    # Initialize session state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    if "message_count" not in st.session_state:
        st.session_state.message_count = 0

    # Display chat history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Input
    if st.session_state.message_count < 10:
        if prompt := st.chat_input(
            "Ask about tenant screening, leases, maintenance..."
        ):
            if not validate_message(prompt):
                st.error("Please enter a message between 1 and 500 characters.")
            # Check for injection
            elif check_prompt_injection(prompt):
                st.error(
                    "I can only assist with topics covered in SASK LLC's property "
                    "management FAQ. Please ask about tenant screening, lease terms, "
                    "maintenance, rent, inspections, or deposits."
                )
            else:
                # Add user message
                st.session_state.chat_messages.append(
                    {"role": "user", "content": prompt}
                )
                st.session_state.message_count += 1

                # Retrieve FAQ entries
                faq_matches = retrieve_faq(prompt, top_k=3)

                # Generate response
                response = generate_chatbot_response(prompt, faq_matches)

                # Add assistant message
                st.session_state.chat_messages.append(
                    {"role": "assistant", "content": response}
                )
                st.rerun()
    else:
        st.warning("Demo API limit (10 queries/session) reached. Please refresh.")

    # Clear button
    if st.button("Clear Chat"):
        st.session_state.chat_messages = []
        st.session_state.message_count = 0
        st.rerun()
