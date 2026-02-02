import time
import logging
from app.api.dependencies import get_orchestrator
from app.repositories.conversation import ConversationRepository

logger = logging.getLogger("service.scheduler")

async def run_scheduler():
    logger.info("Session Timeout Scheduler Started...")
    repo_conv = ConversationRepository()    
    time.sleep(5)

    while True:
        try:
            orchestrator = get_orchestrator()
            stale_sessions = repo_conv.get_stale_sessions(minutes=15)
    
            if stale_sessions:
                logger.info(f"Found {len(stale_sessions)} stale sessions.")

            for session in stale_sessions:
                conv_id, platform, user_id = session
                
                # Synchronous call
                orchestrator.timeout_session(conv_id, platform, user_id)
                
                time.sleep(1)

        except Exception as e:
            logger.error(f"Scheduler Error: {e}")
        
        time.sleep(60)