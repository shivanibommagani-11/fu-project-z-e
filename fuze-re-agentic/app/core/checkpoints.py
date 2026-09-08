"""
Checkpoint management for agent state persistence.
"""

import logging
import json
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class CheckpointManager:
    """In-memory checkpoint manager for agent state persistence."""

    _checkpoints: Dict[str, Dict] = {}

    @classmethod
    def save_checkpoint(cls, session_id: str, checkpoint_id: str, state: Dict[str, Any]) -> None:
        """
        Save agent state checkpoint.

        Args:
            session_id: Session ID
            checkpoint_id: Unique checkpoint ID
            state: State to save
        """
        checkpoint = {
            "session_id": session_id,
            "checkpoint_id": checkpoint_id,
            "state": state,
            "timestamp": datetime.utcnow().isoformat(),
        }

        key = f"{session_id}:{checkpoint_id}"
        cls._checkpoints[key] = checkpoint

        logger.debug(f"Saved checkpoint {checkpoint_id} for session {session_id}")

    @classmethod
    def get_checkpoint(cls, session_id: str, checkpoint_id: str) -> Optional[Dict]:
        """Get checkpoint by ID."""
        key = f"{session_id}:{checkpoint_id}"
        checkpoint = cls._checkpoints.get(key)

        if checkpoint:
            logger.debug(f"Retrieved checkpoint {checkpoint_id}")
            return checkpoint

        return None

    @classmethod
    def get_latest_checkpoint(cls, session_id: str) -> Optional[Dict]:
        """Get latest checkpoint for session."""
        checkpoints = [
            cp for key, cp in cls._checkpoints.items() if key.startswith(f"{session_id}:")
        ]

        if checkpoints:
            latest = sorted(checkpoints, key=lambda x: x["timestamp"], reverse=True)[0]
            logger.debug(f"Retrieved latest checkpoint for session {session_id}")
            return latest

        return None

    @classmethod
    def get_session_checkpoints(cls, session_id: str) -> list:
        """Get all checkpoints for a session."""
        checkpoints = [
            cp for key, cp in cls._checkpoints.items() if key.startswith(f"{session_id}:")
        ]

        return sorted(checkpoints, key=lambda x: x["timestamp"], reverse=True)

    @classmethod
    def delete_checkpoint(cls, session_id: str, checkpoint_id: str) -> None:
        """Delete a checkpoint."""
        key = f"{session_id}:{checkpoint_id}"

        if key in cls._checkpoints:
            del cls._checkpoints[key]
            logger.debug(f"Deleted checkpoint {checkpoint_id}")

    @classmethod
    def delete_session_checkpoints(cls, session_id: str) -> int:
        """Delete all checkpoints for a session."""
        keys_to_delete = [
            key for key in cls._checkpoints.keys() if key.startswith(f"{session_id}:")
        ]

        for key in keys_to_delete:
            del cls._checkpoints[key]

        if keys_to_delete:
            logger.info(f"Deleted {len(keys_to_delete)} checkpoints for session {session_id}")

        return len(keys_to_delete)

    @classmethod
    def cleanup_old_checkpoints(cls, max_age_hours: int = 24) -> int:
        """
        Remove checkpoints older than specified hours.

        Args:
            max_age_hours: Maximum checkpoint age in hours

        Returns:
            Number of checkpoints removed
        """
        cutoff_time = datetime.utcnow().timestamp() - (max_age_hours * 3600)
        removed = 0

        keys_to_remove = []
        for key, checkpoint in cls._checkpoints.items():
            cp_ts = datetime.fromisoformat(checkpoint["timestamp"]).timestamp()
            if cp_ts < cutoff_time:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del cls._checkpoints[key]
            removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} old checkpoints")

        return removed
