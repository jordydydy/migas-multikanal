from app.services.chatbot import ChatbotClient
from app.services.orchestrator import MessageOrchestrator
from app.adapters.whatsapp import WhatsAppAdapter
from app.adapters.instagram import InstagramAdapter
from app.adapters.email.sender import EmailAdapter

_wa_adapter = WhatsAppAdapter()
_ig_adapter = InstagramAdapter()
_email_adapter = EmailAdapter()
_chatbot_client = ChatbotClient()

def get_orchestrator() -> MessageOrchestrator:
    adapters = {
        "whatsapp": _wa_adapter,
        "instagram": _ig_adapter,
        "email": _email_adapter
    }
    return MessageOrchestrator(
        chatbot=_chatbot_client,
        adapters=adapters
    )