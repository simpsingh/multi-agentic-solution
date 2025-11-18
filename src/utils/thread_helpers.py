"""
Thread ID utilities for LangGraph checkpointing.

Supports JWT-based user identification with development fallbacks.
"""
from datetime import datetime
from typing import Optional
import uuid


def generate_thread_id(
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    session_timestamp: Optional[str] = None
) -> str:
    """
    Generate thread_id for LangGraph checkpoint.

    Format: user_{identifier}_session_{timestamp}

    Priority for identifier:
    1. user_id from JWT (production) -> user_{jwt_sub}_session_{timestamp}
    2. session_id from Gradio (development) -> user_session_{gradio_id}_session_{timestamp}
    3. Generated UUID (fallback) -> user_anon_{uuid}_session_{timestamp}

    Args:
        user_id: User ID from JWT token (sub claim)
        session_id: Gradio session ID (development fallback)
        session_timestamp: Optional custom timestamp (ISO format or timestamp string)

    Returns:
        str: Formatted thread_id

    Examples:
        >>> generate_thread_id(user_id="john_doe")
        'user_john_doe_session_20251110_143000'

        >>> generate_thread_id(session_id="gradio_abc123")
        'user_session_gradio_abc123_session_20251110_143000'

        >>> generate_thread_id()
        'user_anon_a1b2c3d4_session_20251110_143000'
    """
    # Determine identifier
    if user_id:
        identifier = user_id
    elif session_id:
        identifier = f"session_{session_id}"
    else:
        # Fallback: generate anonymous UUID
        identifier = f"anon_{uuid.uuid4().hex[:8]}"

    # Generate timestamp
    if session_timestamp is None:
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    elif "T" in session_timestamp:  # ISO format
        dt = datetime.fromisoformat(session_timestamp.replace("Z", "+00:00"))
        session_timestamp = dt.strftime("%Y%m%d_%H%M%S")

    return f"user_{identifier}_session_{session_timestamp}"


def parse_thread_id(thread_id: str) -> dict:
    """
    Parse thread_id to extract user_id and timestamp.

    Args:
        thread_id: Thread ID string (format: user_{id}_session_{timestamp})

    Returns:
        dict: {user_id: str, timestamp: str, is_anonymous: bool}

    Raises:
        ValueError: If thread_id format is invalid

    Examples:
        >>> parse_thread_id("user_john_doe_session_20251110_143000")
        {'user_id': 'john_doe', 'timestamp': '20251110_143000', 'is_anonymous': False}

        >>> parse_thread_id("user_anon_a1b2c3d4_session_20251110_143000")
        {'user_id': 'anon_a1b2c3d4', 'timestamp': '20251110_143000', 'is_anonymous': True}
    """
    try:
        # Split by '_session_' to separate user part from timestamp
        parts = thread_id.split("_session_")
        if len(parts) != 2:
            raise ValueError(f"Invalid thread_id format: {thread_id}")

        user_part = parts[0]  # e.g., "user_john_doe" or "user_anon_a1b2c3d4"
        timestamp = parts[1]  # e.g., "20251110_143000"

        # Extract user_id (remove "user_" prefix)
        if not user_part.startswith("user_"):
            raise ValueError(f"Invalid thread_id format: {thread_id}")

        user_id = user_part[5:]  # Remove "user_" prefix

        # Check if anonymous
        is_anonymous = user_id.startswith("anon_") or user_id.startswith("session_")

        return {
            "user_id": user_id,
            "timestamp": timestamp,
            "is_anonymous": is_anonymous
        }
    except IndexError:
        raise ValueError(f"Invalid thread_id format: {thread_id}")


def validate_thread_id(thread_id: str) -> bool:
    """
    Validate thread_id format.

    Args:
        thread_id: Thread ID string

    Returns:
        bool: True if valid, False otherwise

    Examples:
        >>> validate_thread_id("user_john_doe_session_20251110_143000")
        True

        >>> validate_thread_id("invalid_format")
        False
    """
    try:
        parse_thread_id(thread_id)
        return True
    except ValueError:
        return False
