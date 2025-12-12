from typing import Optional, List, Tuple
from app.repositories.base import Database
from app.core.exceptions import DatabaseError
import logging

logger = logging.getLogger("repo.conversation")

class ConversationRepository:
    def get_active_id(self, platform_id: str, platform: str) -> Optional[str]:
        try:
            with Database.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id, end_timestamp
                        FROM bkpm.conversations
                        WHERE platform_unique_id = %s AND platform = %s
                        ORDER BY start_timestamp DESC
                        LIMIT 1
                        """,
                        (platform_id, platform)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        conversation_id, end_timestamp = row
                        if end_timestamp is None:
                            return str(conversation_id)
            return None
        except Exception as e:
            logger.error(f"Error fetching active conversation: {e}")
            raise DatabaseError("Failed to fetch conversation")

    def get_latest_id(self, platform_id: str, platform: str) -> Optional[str]:
        try:
            with Database.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT id
                        FROM bkpm.conversations
                        WHERE platform_unique_id = %s AND platform = %s
                        ORDER BY start_timestamp DESC
                        LIMIT 1
                        """,
                        (platform_id, platform)
                    )
                    row = cursor.fetchone()
                    return str(row[0]) if row else None
        except Exception as e:
            logger.error(f"Error fetching latest conversation: {e}")
            return None

    def get_stale_sessions(self, minutes: int = 15) -> List[Tuple[str, str, str]]:
        try:
            with Database.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"""
                        SELECT c.id, c.platform, c.platform_unique_id
                        FROM bkpm.conversations c
                        WHERE c.end_timestamp IS NULL 
                        AND c.platform IN ('whatsapp', 'instagram')
                        AND c.start_timestamp >= CURRENT_DATE
                        AND COALESCE(
                            (SELECT MAX(created_at) FROM bkpm.chat_history WHERE session_id = c.id),
                            c.start_timestamp
                        ) < NOW() - INTERVAL '{minutes} minutes'
                        LIMIT 50
                        """
                    )
                    rows = cursor.fetchall()
                    return [(str(row[0]), row[1], row[2]) for row in rows]
        except Exception as e:
            logger.error(f"Error fetching stale sessions: {e}")
            return []

    def close_session(self, conversation_id: str):
        try:
            with Database.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE bkpm.conversations
                        SET end_timestamp = NOW()
                        WHERE id = %s
                        """,
                        (conversation_id,)
                    )
                    conn.commit()
                    logger.info(f"Session {conversation_id} closed successfully.")
        except Exception as e:
            logger.error(f"Error closing session {conversation_id}: {e}")