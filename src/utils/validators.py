"""
Input Validators

Provides input validation and guardrails.
"""

import re
from src.config import settings


def validate_user_input(prompt: str, metadata_id: int | None = None) -> tuple[bool, str | None]:
    """
    Validate user input.

    Args:
        prompt: User prompt
        metadata_id: Optional metadata ID

    Returns:
        tuple: (is_valid, error_message)
    """
    # Check prompt length
    if len(prompt) > settings.MAX_PROMPT_LENGTH:
        return False, f"Prompt exceeds maximum length of {settings.MAX_PROMPT_LENGTH} characters"

    # Check metadata ID
    if metadata_id is not None and metadata_id <= 0:
        return False, "Invalid metadata_id: must be positive integer"

    return True, None


def detect_prompt_injection(prompt: str) -> tuple[bool, str | None]:
    """
    Detect potential prompt injection attempts.

    Args:
        prompt: User prompt

    Returns:
        tuple: (is_suspicious, detected_pattern)
    """
    suspicious_patterns = [
        r"ignore\s+(previous|all|above)\s+instructions",
        r"forget\s+your\s+role",
        r"you\s+are\s+now\s+a",
        r"act\s+as\s+(admin|hacker|root)",
        r"system:",
        r"assistant:",
        r"<\|im_start\|>",
        r"developer\s+mode",
        r"sudo\s+mode",
        r"god\s+mode",
        r"base64:",
        r"rot13:",
    ]

    prompt_lower = prompt.lower()

    for pattern in suspicious_patterns:
        if re.search(pattern, prompt_lower):
            return True, pattern

    return False, None


def validate_thread_id(thread_id: str) -> bool:
    """
    Validate thread ID format.

    Args:
        thread_id: Thread identifier

    Returns:
        bool: True if valid
    """
    # Expected format: user_{user_id}_session_{timestamp}
    pattern = r"^user_[\w]+_session_[\d]+$"
    return bool(re.match(pattern, thread_id))
