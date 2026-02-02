import time
from typing import Dict, Any
from app.schemas.models import IncomingMessage
from app.services.chatbot import ChatbotClient
from app.adapters.base import BaseAdapter
from app.core.config import settings
import logging

logger = logging.getLogger("service.orchestrator")

_SESSION_STORE: Dict[str, str] = {}

class MessageOrchestrator:
    def __init__(
        self, 
        chatbot: ChatbotClient,
        adapters: Dict[str, BaseAdapter]
    ):
        self.chatbot = chatbot
        self.adapters = adapters

    def _get_conversation_id(self, user_id: str) -> str:
        return _SESSION_STORE.get(user_id, "")

    def _set_conversation_id(self, user_id: str, conversation_id: str):
        if conversation_id:
            _SESSION_STORE[user_id] = conversation_id

    def handle_feedback(self, msg: IncomingMessage):
        payload_str = msg.metadata.get("payload", "")
        user_id = msg.platform_unique_id
        
        if "-" not in payload_str: 
            return

        try:
            rating_raw, message_id = payload_str.split("-", 1)
            
            rating = "like" if "like" in rating_raw.lower() or "good" in rating_raw.lower() else "dislike"
            
            content = f"Feedback received via {msg.platform}"
            
            self.chatbot.send_feedback(message_id, rating, user_id, content)
            
            adapter = self.adapters.get(msg.platform)
            if adapter:
                adapter.send_message(user_id, "Terima kasih atas masukan Anda!")
                
        except Exception as e:
            logger.error(f"Handle Feedback Error: {e}")

    def process_message(self, msg: IncomingMessage):
        adapter = self.adapters.get(msg.platform)
        if not adapter: 
            return

        user_id = msg.platform_unique_id
        current_conv_id = self._get_conversation_id(user_id)

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
            
            dify_message_id = resp.get("id") 
            
            if new_conv_id:
                self._set_conversation_id(user_id, new_conv_id)
            
            send_kwargs = {}
            if msg.platform == "email":
                send_kwargs["subject"] = f"Re: {msg.metadata.get('subject', 'Inquiry')}"
                if settings.EMAIL_PROVIDER == "azure_oauth2":
                    send_kwargs["graph_message_id"] = msg.metadata.get("graph_message_id")
                else:
                    send_kwargs["in_reply_to"] = msg.metadata.get("message_id")

            adapter.send_message(user_id, answer, **send_kwargs)
            
            if dify_message_id and len(answer) > 10:
                adapter.send_feedback_request(user_id, dify_message_id)

        try: 
            adapter.send_typing_off(user_id)
        except Exception: 
            pass