"""Input validation and security checks."""


def check_prompt_injection(message: str) -> bool:
    """
    Detect common prompt injection patterns.

    Returns True if injection pattern detected, False otherwise.
    """
    patterns = ["ignore", "forget", "bypass", "jailbreak"]
    message_lower = message.lower()

    for pattern in patterns:
        if pattern in message_lower:
            return True

    return False


def validate_message(message: str, max_length: int = 500) -> bool:
    """
    Validate message length and content.

    Returns True if valid, False otherwise.
    """
    if not message or not isinstance(message, str):
        return False

    if len(message) > max_length:
        return False

    return True
