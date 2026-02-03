import requests
import logging
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger("service.chatbot")

class ChatbotClient:
    def __init__(self):
        self.base_url = settings.DIFY_API_BASE_URL.rstrip("/")
        self.api_key = settings.DIFY_API_KEY

    def send_message(self, query: str, user_id: str, conversation_id: str = None, inputs: dict = None) -> Dict[str, Any]:
        url = f"{self.base_url}/chat-messages"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "inputs": inputs or {},
            "query": query,
            "response_mode": "blocking",
            "user": user_id,
            "conversation_id": conversation_id if conversation_id else "",
            "files": []
        }
        
        logger.info(f"Send to Dify [User: {user_id}]: {query[:50]}...")
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Dify API Error: {e}")
            if e.response:
                logger.error(f"Response: {e.response.text}")
            return {"error": str(e)}
            
    def send_feedback(self, message_id: str, rating: str, user_id: str, content: str = None) -> bool:
        url = f"{self.base_url}/messages/{message_id}/feedbacks"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "rating": rating,
            "user": user_id,
            "content": content
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            return resp.ok
        except Exception as e:
            logger.error(f"Feedback Error: {e}")
            return False