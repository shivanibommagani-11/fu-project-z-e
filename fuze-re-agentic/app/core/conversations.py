"""
Conversation history and session management.
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationManager:
    """In-memory conversation history manager."""

    _conversations: Dict[str, Dict] = {}

    @classmethod
    def create_session(cls, session_id: str, user_id: str) -> Dict:
        """
        Create a new conversation session.

        Args:
            session_id: Unique session ID
            user_id: User ID

        Returns:
            Session dict
        """
        logger.info(f"[CONV] Creating new session: {session_id} for user: {user_id}")

        session = {
            "session_id": session_id,
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "messages": [],
            "metadata": {},
        }

        cls._conversations[session_id] = session
        logger.info(f"[CONV] ✓ Session created: {session_id}")
        logger.info(f"[CONV] Total active sessions: {len(cls._conversations)}")
        return session

    @classmethod
    def get_session(cls, session_id: str) -> Optional[Dict]:
        """Get session by ID."""
        session = cls._conversations.get(session_id)
        if session:
            logger.info(f"[CONV] ✓ Session found: {session_id} ({len(session.get('messages', []))} messages)")
        else:
            logger.info(f"[CONV] Session not found: {session_id}")
        return session

    @classmethod
    def add_message(cls, session_id: str, role: str, content: str) -> None:
        """
        Add message to conversation.

        Args:
            session_id: Session ID
            role: Message role (user, assistant, system)
            content: Message content
        """
        logger.info(f"[CONV] Adding {role} message to session {session_id}: {content[:50]}...")
        session = cls.get_session(session_id)

        if not session:
            logger.warning(f"[CONV] Cannot add message - Session {session_id} not found")
            return

        session["messages"].append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        session["updated_at"] = datetime.utcnow().isoformat()
        logger.info(f"[CONV] ✓ Added {role} message - total messages in session: {len(session['messages'])}")

    @classmethod
    def get_messages(cls, session_id: str) -> List[Dict]:
        """Get conversation messages."""
        logger.info(f"[CONV] Retrieving messages for session: {session_id}")
        session = cls.get_session(session_id)

        if not session:
            logger.warning(f"[CONV] Cannot retrieve messages - session not found")
            return []

        messages = [{"role": m["role"], "content": m["content"]} for m in session["messages"]]
        logger.info(f"[CONV] ✓ Retrieved {len(messages)} messages")
        for i, msg in enumerate(messages):
            logger.info(f"[CONV]   Message {i}: role={msg['role']}, content_len={len(msg['content'])}")

        # Return only role and content (for LLM)
        return messages

    @classmethod
    def get_full_history(cls, session_id: str) -> Optional[Dict]:
        """Get complete session history."""
        return cls.get_session(session_id)

    @classmethod
    def clear_session(cls, session_id: str) -> None:
        """Clear a session."""
        if session_id in cls._conversations:
            del cls._conversations[session_id]
            logger.info(f"Cleared session {session_id}")

    @classmethod
    def set_metadata(cls, session_id: str, key: str, value) -> None:
        """Set session metadata."""
        session = cls.get_session(session_id)

        if session:
            session["metadata"][key] = value
            logger.debug(f"Set metadata {key} for session {session_id}")

    @classmethod
    def get_metadata(cls, session_id: str, key: str) -> Optional:
        """Get session metadata."""
        session = cls.get_session(session_id)

        if session:
            return session["metadata"].get(key)

        return None

    @classmethod
    def get_all_sessions(cls) -> Dict[str, Dict]:
        """Get all active sessions."""
        return cls._conversations.copy()

    @classmethod
    def cleanup_old_sessions(cls, max_age_hours: int = 24) -> int:
        """
        Remove sessions older than specified hours.

        Args:
            max_age_hours: Maximum session age in hours

        Returns:
            Number of sessions removed
        """
        import time

        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        removed = 0

        sessions_to_remove = []
        for session_id, session in cls._conversations.items():
            created_ts = datetime.fromisoformat(session["created_at"]).timestamp()
            if created_ts < cutoff_time:
                sessions_to_remove.append(session_id)

        for session_id in sessions_to_remove:
            cls.clear_session(session_id)
            removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} old sessions")

        return removed
