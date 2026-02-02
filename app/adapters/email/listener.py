import imaplib
import email
import time
import asyncio
import logging
import requests
from email.header import decode_header
from typing import Dict, Any, Optional

from app.core.config import settings
from app.adapters.email.utils import sanitize_email_body
from app.repositories.message import MessageRepository
from app.api.dependencies import get_orchestrator
from app.schemas.models import IncomingMessage

logger = logging.getLogger("email.listener")
repo = MessageRepository()

import msal
_token_cache: Dict[str, Any] = {}

def get_graph_token() -> Optional[str]:
    global _token_cache
    if _token_cache and _token_cache.get("expires_at", 0) > time.time() + 60:
        return _token_cache.get("access_token")
    if not all([settings.AZURE_CLIENT_ID, settings.AZURE_CLIENT_SECRET, settings.AZURE_TENANT_ID]):
        return None
    try:
        app = msal.ConfidentialClientApplication(
            settings.AZURE_CLIENT_ID,
            authority=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}",
            client_credential=settings.AZURE_CLIENT_SECRET,
        )
        result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
        if "access_token" in result:
            _token_cache = {
                "access_token": result["access_token"],
                "expires_at": time.time() + result.get("expires_in", 3500)
            }
            return result["access_token"]
        return None
    except Exception: 
        return None

def _mark_graph_read(user_id, message_id, token):
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/messages/{message_id}"
    try:
        requests.patch(url, json={"isRead": True}, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=5)
    except Exception: 
        pass

def _process_graph_message(user_id, msg, token):
    graph_id = msg.get("id")
    azure_conv_id = msg.get("conversationId") 
    
    if not graph_id: 
        return

    if repo.is_processed(graph_id, "email"):
        logger.warning(f"DUPLIKASI DITOLAK: {graph_id}. Menandai sebagai Read.")
        _mark_graph_read(user_id, graph_id, token)
        return

    _mark_graph_read(user_id, graph_id, token)

    clean_body = _extract_graph_body(msg)
    sender_info = msg.get("from", {}).get("emailAddress", {})
    
    metadata = {
        "subject": msg.get("subject", "No Subject"),
        "sender_name": sender_info.get("name", ""),
        "graph_message_id": graph_id,
        "conversation_id": azure_conv_id 
    }

    process_single_email(sender_info.get("address", ""), clean_body, metadata)

def _extract_graph_body(msg):
    body_content = msg.get("body", {}).get("content", "")
    body_type = msg.get("body", {}).get("contentType", "Text")
    return sanitize_email_body(None, body_content) if body_type.lower() == "html" else sanitize_email_body(body_content, None)

def _poll_graph_api():
    token = get_graph_token()
    if not token: 
        return
    user_id = settings.AZURE_EMAIL_USER
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}/mailFolders/inbox/messages"
    params = {"$filter": "isRead eq false", "$top": 10}
    try:
        resp = requests.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=20)
        if resp.status_code == 200:
            for msg in resp.json().get("value", []):
                _process_graph_message(user_id, msg, token)
    except Exception as e:
        logger.error(f"Graph Polling Error: {e}")

def _connect_gmail_imap():
    try:
        email_user = settings.EMAIL_USER.strip('"\'')
        email_pass = settings.EMAIL_PASS.strip('"\'')
        
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=30)
        mail.login(email_user, email_pass)
        return mail
    except imaplib.IMAP4.error as e:
        logger.error(f"IMAP Login Error: {e}")
        logger.error("Check: 1) IMAP enabled in Gmail, 2) Using App Password, 3) 2FA enabled")
        return None
    except Exception as e:
        logger.error(f"IMAP Connection Error: {e}")
        return None

def _process_gmail_message(mail, msg_id):
    try:
        status, msg_data = mail.fetch(msg_id, "(RFC822)")
        
        if status != "OK":
            return
        
        email_body = msg_data[0][1]
        email_message = email.message_from_bytes(email_body)
        
        message_id = email_message.get("Message-ID", "").strip()
        
        if not message_id:
            logger.warning(f"Email {msg_id} has no Message-ID, skipping")
            return
        
        if repo.is_processed(message_id, "email"):
            logger.debug(f"Email {message_id[:30]}... already processed")
            mail.store(msg_id, '+FLAGS', '\\Seen')
            return
        
        mail.store(msg_id, '+FLAGS', '\\Seen')
        
        from_header = email_message.get("From", "")
        import re
        email_match = re.search(r'<(.+?)>', from_header)
        sender_email = email_match.group(1) if email_match else from_header
        
        sender_lower = sender_email.lower()
        if any(skip in sender_lower for skip in ["mailer-daemon", "noreply", "no-reply", "postmaster"]):
            logger.info(f"Skipping system email from: {sender_email}")
            return
        
        subject = email_message.get("Subject", "No Subject")
        if subject and subject != "No Subject":
            decoded = decode_header(subject)[0]
            if isinstance(decoded[0], bytes):
                subject = decoded[0].decode(decoded[1] or "utf-8", errors="ignore")
            else:
                subject = decoded[0]
        
        body = ""
        html_body = ""
        
        if email_message.is_multipart():
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                if "attachment" in content_disposition:
                    continue
                
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        if content_type == "text/plain" and not body:
                            body = payload.decode(errors="ignore")
                        elif content_type == "text/html" and not html_body:
                            html_body = payload.decode(errors="ignore")
                except Exception:
                    continue
        else:
            try:
                payload = email_message.get_payload(decode=True)
                if payload:
                    content_type = email_message.get_content_type()
                    decoded_payload = payload.decode(errors="ignore")
                    if content_type == "text/html":
                        html_body = decoded_payload
                    else:
                        body = decoded_payload
            except Exception:
                pass
        
        clean_body = sanitize_email_body(body, html_body)
        
        if not clean_body or len(clean_body.strip()) < 3:
            logger.warning(f"Email has no readable content: {subject}")
            return
        
        in_reply_to = email_message.get("In-Reply-To", "")
        references = email_message.get("References", "")
        
        thread_key = in_reply_to or message_id
        
        metadata = {
            "subject": subject,
            "sender_name": from_header,
            "message_id": message_id,
            "in_reply_to": in_reply_to,
            "references": references,
            "thread_key": thread_key
        }
        
        logger.info(f"Processing email from {sender_email}: {subject[:50]}")
        
        # Process the email
        process_single_email(sender_email, clean_body, metadata)
        
    except Exception as e:
        logger.error(f"Error processing Gmail message {msg_id}: {e}")
        import traceback
        traceback.print_exc()

def _poll_gmail_imap():
    mail = _connect_gmail_imap()
    
    if not mail:
        logger.error("Could not connect to Gmail IMAP")
        return
    
    try:
        status, messages = mail.select("INBOX")
        
        if status != "OK":
            logger.error(f"Failed to select INBOX: {status}")
            return
        
        status, msg_ids = mail.search(None, "UNSEEN")
        
        if status != "OK":
            logger.error("Failed to search for unread messages")
            return
        
        unread_ids = msg_ids[0].split()
        
        if unread_ids:
            logger.info(f"Found {len(unread_ids)} unread email(s)")
            
            for msg_id in unread_ids:
                _process_gmail_message(mail, msg_id)
                
                time.sleep(0.5)
        else:
            logger.debug("No unread emails")
        
    except Exception as e:
        logger.error(f"Gmail polling error: {e}")
    finally:
        try:
            mail.logout()
        except:
            pass

def process_single_email(sender_email, body, metadata: dict):
    if "mailer-daemon" in sender_email.lower() or "noreply" in sender_email.lower(): 
        return

    msg = IncomingMessage(
        platform_unique_id=sender_email,
        query=body,
        platform="email",
        metadata=metadata
    )
    
    try:
        orchestrator = get_orchestrator()
        orchestrator.process_message(msg)
        logger.info(f"Email processed: {sender_email}")
    except Exception as err:
        logger.error(f"Internal Process Error: {err}")
        import traceback
        traceback.print_exc()

def start_email_listener():
    if not settings.EMAIL_USER and not settings.AZURE_CLIENT_ID: 
        logger.warning("No email credentials configured")
        return
    
    provider = settings.EMAIL_PROVIDER
    logger.info(f"Starting Email Listener (Provider: {provider})")
    
    while True:
        try:
            if provider == "azure_oauth2":
                _poll_graph_api()
            elif provider == "gmail":
                _poll_gmail_imap()
            else:
                logger.warning(f"Unknown email provider: {provider}")
                
        except Exception as e:
            logger.error(f"Email listener error: {e}")
        
        time.sleep(settings.EMAIL_POLL_INTERVAL_SECONDS)