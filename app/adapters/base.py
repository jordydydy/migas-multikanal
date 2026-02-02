from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import time

class BaseAdapter(ABC):
    @abstractmethod
    def send_message(self, recipient_id: str, text: str, **kwargs) -> Dict[str, Any]:
        pass

    def send_typing_on(self, recipient_id: str, message_id: Optional[str] = None):
        # Base implementation for turning off typing indicators.
        pass

    def send_typing_off(self, recipient_id: str):
        # Base implementation for turning off typing indicators.
        pass
    
    def send_feedback_request(self, recipient_id: str, answer_id: int) -> Dict[str, Any]:
        # Synchronous no-op
        return {"sent": False, "reason": "Not implemented"}