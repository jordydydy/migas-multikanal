import time
from typing import Dict, Any, List
from app.schemas.models import IncomingMessage
from app.services.chatbot import ChatbotClient
from app.adapters.base import BaseAdapter
from app.repositories.conversation import ConversationRepository
from app.core.config import settings
import logging

logger = logging.getLogger("service.orchestrator")

RESET_KEYWORDS: List[str] = [
    "terima kasih", "terimakasih", "makasih", "trimakasih", "trims",
    "thank you", "thankyou", "thanks"
]

class MessageOrchestrator:
    def __init__(
        self, 
        chatbot: ChatbotClient,
        adapters: Dict[str, BaseAdapter]
    ):
        self.chatbot = chatbot
        self.adapters = adapters
        self.repo_conv = ConversationRepository()

    def timeout_session(self, user_id: str, platform: str):
        adapter = self.adapters.get(platform)
        if adapter:
            try:
                timeout_msg = "Sesi Anda telah berakhir. Silakan kirim pesan baru untuk memulai percakapan kembali."
                adapter.send_message(user_id, timeout_msg)
            except Exception as e:
                logger.error(f"Failed to send timeout message to {user_id}: {e}")
        
        self.repo_conv.clear_session(user_id)

    def handle_feedback(self, msg: IncomingMessage):
        return

    def process_message(self, msg: IncomingMessage):
        adapter = self.adapters.get(msg.platform)
        if not adapter: 
            return

        user_id = msg.platform_unique_id
        
        clean_query = msg.query.strip().lower()
        
        is_reset = any(keyword in clean_query for keyword in RESET_KEYWORDS)

        if is_reset:
            logger.info(f"User {user_id} sent reset keyword. Clearing local session.")
            
            reply_text = "Sama-sama! Senang bisa membantu. Sesi percakapan ini telah di-akhiri."
            adapter.send_message(user_id, reply_text)
            
            self.repo_conv.clear_session(user_id)
            return

        current_conv_id = self.repo_conv.get_active_session(user_id, msg.platform)
        
        try:
            msg_id = msg.metadata.get("message_id") if msg.metadata else None
            adapter.send_typing_on(user_id, message_id=msg_id)
            if msg.platform == "whatsapp" and msg_id and hasattr(adapter, 'mark_as_read'):
                adapter.mark_as_read(msg_id)
        except Exception: 
            pass

        inputs = {
            "platform": msg.platform,
            "sender_name": msg.metadata.get("sender_name", "Unknown")
        }
        
        resp = self.chatbot.send_message(
            query=msg.query,
            user_id=user_id,
            conversation_id=current_conv_id,
            inputs=inputs
        )
        
        if "error" in resp:
            logger.error(f"Dify Error: {resp['error']}")
            adapter.send_message(user_id, "Mohon maaf, sistem sedang sibuk. Silakan coba lagi nanti.")
        else:
            answer = resp.get("answer", "")
            new_conv_id = resp.get("conversation_id")
            
            # 4. Save new ID to DB
            if new_conv_id:
                self.repo_conv.save_session(user_id, msg.platform, new_conv_id)
            
            send_kwargs = {}
            if msg.platform == "email":
                send_kwargs["subject"] = f"Re: {msg.metadata.get('subject', 'Inquiry')}"
                if settings.EMAIL_PROVIDER == "azure_oauth2":
                    send_kwargs["graph_message_id"] = msg.metadata.get("graph_message_id")
                else:
                    send_kwargs["in_reply_to"] = msg.metadata.get("message_id")

            adapter.send_message(user_id, answer, **send_kwargs)

        try: 
            adapter.send_typing_off(user_id)
        except Exception: 
            pass