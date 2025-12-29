import re
import logging
from app.core.config import settings
from app.adapters.base import BaseAdapter
from app.adapters.utils import split_text_smartly, make_meta_request

logger = logging.getLogger("adapters.instagram")

class InstagramAdapter(BaseAdapter):
    def __init__(self):
        self.version = "v24.0"
        self.base_url = f"https://graph.instagram.com/{self.version}/{settings.INSTAGRAM_CHATBOT_ID}/messages"
        self.token = settings.INSTAGRAM_PAGE_ACCESS_TOKEN

    def _clean_id(self, user_id: str) -> str:
        return user_id.replace('@instagram.com', '').strip()

    async def send_typing_on(self, recipient_id: str, message_id: str = None):
        if not self.token: return
        payload = {"recipient": {"id": self._clean_id(recipient_id)}, "sender_action": "typing_on"}
        result = await make_meta_request("POST", self.base_url, self.token, payload)

    async def send_typing_off(self, recipient_id: str):
        if not self.token: return
        payload = {"recipient": {"id": self._clean_id(recipient_id)}, "sender_action": "typing_off"}
        result = await make_meta_request("POST", self.base_url, self.token, payload)

    async def send_message(self, recipient_id: str, text: str, **kwargs):
        if not self.token: return {"success": False}
        
        text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
        chunks = split_text_smartly(text, 1000)
        
        results = []
        for chunk in chunks:
            payload = {
                "recipient": {"id": self._clean_id(recipient_id)},
                "message": {"text": chunk}
            }
            res = await make_meta_request("POST", self.base_url, self.token, payload)
            results.append(res)
            
            status = res.get("status_code")
            if status == 200:
                logger.info(f"[Instagram API] Message sent: 200 OK")
            else:
                logger.error(f"[Instagram API] Message failed: {status} - {res.get('data')}")
            
        return {"sent": True, "results": results}

    async def send_feedback_request(self, recipient_id: str, answer_id: int):
        if not self.token: return {"success": False}
        
        payload = {
            "recipient": {"id": self._clean_id(recipient_id)},
            "message": {
                "text": "Apakah jawaban ini membantu?",
                "quick_replies": [
                    {"content_type": "text", "title": "Yes", "payload": f"good-{answer_id}"},
                    {"content_type": "text", "title": "No", "payload": f"bad-{answer_id}"}
                ]
            }
        }
        result = await make_meta_request("POST", self.base_url, self.token, payload)
        
        status = result.get("status_code")
        if status == 200:
            logger.info(f"[Instagram API] Feedback request sent: 200 OK")
        else:
            logger.error(f"[Instagram API] Feedback request failed: {status} - {result.get('data')}")
        
        return result