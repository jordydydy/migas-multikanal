"""
Gmail IMAP Access Diagnostic Test
Quick test to check if IMAP is enabled and working
"""

import imaplib
import email
import sys
from email.header import decode_header
from app.core.config import settings

# ANSI color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")


def test_gmail_imap():
    """Test Gmail IMAP access"""
    
    print_header("GMAIL IMAP DIAGNOSTIC TEST")
    
    # Check configuration
    print_info("Configuration:")
    print(f"  Email: {settings.EMAIL_USER}")
    print(f"  Provider: {settings.EMAIL_PROVIDER}")
    
    if not settings.EMAIL_USER or not settings.EMAIL_PASS:
        print_error("EMAIL_USER or EMAIL_PASS not configured!")
        return False
    
    # Remove quotes from email if present
    email_user = settings.EMAIL_USER.strip('"\'')
    email_pass = settings.EMAIL_PASS.strip('"\'')
    
    print(f"\n{Colors.YELLOW}Attempting IMAP connection...{Colors.RESET}\n")
    
    try:
        # Connect to Gmail IMAP
        print_info("Step 1: Connecting to imap.gmail.com:993...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=30)
        print_success("Connected to Gmail IMAP server")
        
        # Login
        print_info(f"Step 2: Authenticating as {email_user}...")
        mail.login(email_user, email_pass)
        print_success("Authentication successful!")
        
        # Select inbox
        print_info("Step 3: Selecting INBOX...")
        status, messages = mail.select("INBOX")
        
        if status != "OK":
            print_error(f"Failed to select INBOX: {status}")
            return False
        
        msg_count = int(messages[0])
        print_success(f"Successfully accessed INBOX ({msg_count} messages)")
        
        # Search for unread messages
        print_info("\nStep 4: Searching for UNREAD messages...")
        status, msg_ids = mail.search(None, "UNSEEN")
        
        if status != "OK":
            print_warning("Could not search for unread messages")
        else:
            unread_ids = msg_ids[0].split()
            unread_count = len(unread_ids)
            
            if unread_count > 0:
                print_success(f"Found {unread_count} UNREAD messages")
                
                # Show first unread message
                print_info("\nFirst unread message details:")
                first_id = unread_ids[0]
                status, msg_data = mail.fetch(first_id, "(RFC822)")
                
                if status == "OK":
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    # Get subject
                    subject = email_message["Subject"]
                    if subject:
                        decoded = decode_header(subject)[0]
                        if isinstance(decoded[0], bytes):
                            subject = decoded[0].decode(decoded[1] or "utf-8")
                        else:
                            subject = decoded[0]
                    else:
                        subject = "(no subject)"
                    
                    from_header = email_message.get("From", "Unknown")
                    date_header = email_message.get("Date", "Unknown")
                    message_id = email_message.get("Message-ID", "Unknown")
                    
                    print(f"  Subject: {subject}")
                    print(f"  From: {from_header}")
                    print(f"  Date: {date_header}")
                    print(f"  Message-ID: {message_id[:50]}...")
                    
                    # Get body
                    body = ""
                    if email_message.is_multipart():
                        for part in email_message.walk():
                            if part.get_content_type() == "text/plain":
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                    else:
                        body = email_message.get_payload(decode=True).decode(errors="ignore")
                    
                    if body:
                        print(f"\n  Body preview:")
                        print(f"  {body[:200].strip()}...")
                
            else:
                print_warning("No unread messages found")
                print_info("Try sending yourself an email to test")
        
        # Get recent messages
        print_info("\nStep 5: Fetching last 3 messages (read or unread)...")
        status, msg_ids = mail.search(None, "ALL")
        
        if status == "OK":
            all_ids = msg_ids[0].split()
            recent_ids = all_ids[-3:] if len(all_ids) >= 3 else all_ids
            
            print_success(f"Found {len(all_ids)} total messages")
            
            for i, msg_id in enumerate(reversed(recent_ids), 1):
                status, msg_data = mail.fetch(msg_id, "(RFC822)")
                
                if status == "OK":
                    email_body = msg_data[0][1]
                    email_message = email.message_from_bytes(email_body)
                    
                    subject = email_message.get("Subject", "(no subject)")
                    if subject and subject != "(no subject)":
                        decoded = decode_header(subject)[0]
                        if isinstance(decoded[0], bytes):
                            subject = decoded[0].decode(decoded[1] or "utf-8")
                        else:
                            subject = decoded[0]
                    
                    from_header = email_message.get("From", "Unknown")
                    
                    print(f"\n  {i}. {subject}")
                    print(f"     From: {from_header}")
        
        # Close connection
        mail.logout()
        
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ IMAP ACCESS IS WORKING!{Colors.RESET}")
        print(f"\n{Colors.YELLOW}Your email listener should work now.{Colors.RESET}")
        print_info("If the listener still doesn't work, check:")
        print("  1. Email listener is actually running")
        print("  2. No firewall blocking IMAP port 993")
        print("  3. EMAIL_POLL_INTERVAL_SECONDS in .env")
        
        return True
        
    except imaplib.IMAP4.error as e:
        print_error(f"IMAP Authentication Error: {e}")
        print(f"\n{Colors.YELLOW}Common causes:{Colors.RESET}")
        print("  1. IMAP not enabled in Gmail settings")
        print("  2. Wrong App Password")
        print("  3. 2-Factor Authentication not enabled")
        
        print(f"\n{Colors.YELLOW}To fix:{Colors.RESET}")
        print("  1. Go to Gmail → Settings → Forwarding and POP/IMAP")
        print("  2. Enable IMAP")
        print("  3. Make sure you're using App Password, not regular password")
        print("  4. Generate new App Password: https://myaccount.google.com/apppasswords")
        
        return False
        
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    try:
        success = test_gmail_imap()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Test interrupted{Colors.RESET}")
        sys.exit(130)


if __name__ == "__main__":
    main()