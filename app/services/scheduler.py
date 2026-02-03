import time
import logging
from app.repositories.conversation import ConversationRepository
from app.api.dependencies import get_orchestrator

logger = logging.getLogger("service.scheduler")

def run_scheduler():
    logger.info("Session Timeout Scheduler Started (3 Minutes Policy)...")
    repo_conv = ConversationRepository()    
    
    time.sleep(5)

    while True:
        try:
            stale_sessions = repo_conv.get_stale_sessions(seconds=180)
    
            if stale_sessions:
                logger.info(f"Found {len(stale_sessions)} stale sessions.")
                
                orchestrator = get_orchestrator()

                for session in stale_sessions:
                    user_id, platform, conversation_id = session
                    
                    orchestrator.timeout_session(user_id, platform)
                    
                    logger.info(f"Session timeout processed for {user_id}")

        except Exception as e:
            logger.error(f"Scheduler Error: {e}")
        
        time.sleep(30)