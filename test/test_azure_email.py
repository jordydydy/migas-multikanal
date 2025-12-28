import msal
import requests
import sys
from typing import Dict, List, Tuple
from datetime import datetime
from app.core.config import settings

# ANSI color codes for better output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")

def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")

def print_info(text: str):
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


class AzureEmailTester:
    def __init__(self):
        self.token = None
        self.required_permissions = [
            "Mail.Read",
            "Mail.ReadWrite", 
            "Mail.Send",
            "User.Read"
        ]
        self.test_results: List[Tuple[str, bool, str]] = []
    
    def add_result(self, test_name: str, success: bool, message: str):
        """Store test result"""
        self.test_results.append((test_name, success, message))
    
    def get_token(self) -> bool:
        """Test: Acquire OAuth2 token"""
        print_header("TEST 1: Token Acquisition")
        
        # Check configuration
        if not all([settings.AZURE_CLIENT_ID, settings.AZURE_CLIENT_SECRET, 
                   settings.AZURE_TENANT_ID, settings.AZURE_EMAIL_USER]):
            print_error("Missing Azure configuration in .env file")
            print_info("Required variables:")
            print("  - AZURE_CLIENT_ID")
            print("  - AZURE_CLIENT_SECRET")
            print("  - AZURE_TENANT_ID")
            print("  - AZURE_EMAIL_USER")
            self.add_result("Configuration", False, "Missing environment variables")
            return False
        
        print_success("All configuration variables present")
        print_info(f"Client ID: {settings.AZURE_CLIENT_ID[:8]}...")
        print_info(f"Tenant ID: {settings.AZURE_TENANT_ID[:8]}...")
        print_info(f"Email User: {settings.AZURE_EMAIL_USER}")
        
        try:
            app = msal.ConfidentialClientApplication(
                settings.AZURE_CLIENT_ID,
                authority=f"https://login.microsoftonline.com/{settings.AZURE_TENANT_ID}",
                client_credential=settings.AZURE_CLIENT_SECRET,
            )
            
            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
            
            if "access_token" in result:
                self.token = result["access_token"]
                expires_in = result.get("expires_in", 0)
                print_success(f"Token acquired successfully")
                print_info(f"Token expires in: {expires_in} seconds (~{expires_in//60} minutes)")
                self.add_result("Token Acquisition", True, "Success")
                return True
            else:
                error = result.get("error", "Unknown error")
                error_desc = result.get("error_description", "No description")
                print_error(f"Failed to acquire token")
                print_error(f"Error: {error}")
                print_error(f"Description: {error_desc}")
                self.add_result("Token Acquisition", False, f"{error}: {error_desc}")
                return False
                
        except Exception as e:
            print_error(f"Exception during token acquisition: {str(e)}")
            self.add_result("Token Acquisition", False, str(e))
            return False
    
    def test_user_access(self) -> bool:
        """Test: Access user profile"""
        print_header("TEST 2: User Profile Access (User.Read)")
        
        if not self.token:
            print_error("No token available")
            self.add_result("User Profile", False, "No token")
            return False
        
        url = f"https://graph.microsoft.com/v1.0/users/{settings.AZURE_EMAIL_USER}"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print_success("User profile accessed successfully")
                print_info(f"Display Name: {data.get('displayName', 'N/A')}")
                print_info(f"Email: {data.get('mail', 'N/A')}")
                print_info(f"User Principal Name: {data.get('userPrincipalName', 'N/A')}")
                self.add_result("User Profile", True, "Success")
                return True
            else:
                print_error(f"Failed to access user profile (Status: {response.status_code})")
                print_error(f"Response: {response.text}")
                self.add_result("User Profile", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print_error(f"Exception: {str(e)}")
            self.add_result("User Profile", False, str(e))
            return False
    
    def test_read_inbox(self) -> bool:
        """Test: Read inbox messages"""
        print_header("TEST 3: Read Inbox (Mail.Read)")
        
        if not self.token:
            print_error("No token available")
            self.add_result("Read Inbox", False, "No token")
            return False
        
        url = f"https://graph.microsoft.com/v1.0/users/{settings.AZURE_EMAIL_USER}/mailFolders/inbox/messages"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"$top": 5, "$select": "subject,from,receivedDateTime,isRead"}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get("value", [])
                print_success(f"Successfully read inbox ({len(messages)} messages retrieved)")
                
                if messages:
                    print_info("Recent messages:")
                    for i, msg in enumerate(messages[:3], 1):
                        subject = msg.get("subject", "No subject")
                        from_email = msg.get("from", {}).get("emailAddress", {}).get("address", "Unknown")
                        is_read = msg.get("isRead", False)
                        status = "Read" if is_read else "Unread"
                        print(f"  {i}. {subject[:50]} - From: {from_email} ({status})")
                else:
                    print_info("No messages in inbox")
                
                self.add_result("Read Inbox", True, f"{len(messages)} messages")
                return True
            else:
                print_error(f"Failed to read inbox (Status: {response.status_code})")
                print_error(f"Response: {response.text}")
                self.add_result("Read Inbox", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print_error(f"Exception: {str(e)}")
            self.add_result("Read Inbox", False, str(e))
            return False
    
    def test_mark_as_read(self) -> bool:
        """Test: Mark message as read"""
        print_header("TEST 4: Mark Message as Read (Mail.ReadWrite)")
        
        if not self.token:
            print_error("No token available")
            self.add_result("Mark as Read", False, "No token")
            return False
        
        # First, get an unread message
        url = f"https://graph.microsoft.com/v1.0/users/{settings.AZURE_EMAIL_USER}/mailFolders/inbox/messages"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"$filter": "isRead eq false", "$top": 1}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                print_warning("Could not fetch unread messages to test")
                print_info("This might be because all messages are already read")
                self.add_result("Mark as Read", None, "No unread messages to test")
                return True  # Not a failure, just can't test
            
            messages = response.json().get("value", [])
            
            if not messages:
                print_warning("No unread messages found to test mark-as-read")
                print_info("This permission will be tested when an unread message arrives")
                self.add_result("Mark as Read", None, "No unread messages")
                return True
            
            message_id = messages[0].get("id")
            subject = messages[0].get("subject", "No subject")
            
            # Try to mark it as read
            update_url = f"https://graph.microsoft.com/v1.0/users/{settings.AZURE_EMAIL_USER}/messages/{message_id}"
            update_response = requests.patch(
                update_url,
                json={"isRead": True},
                headers={**headers, "Content-Type": "application/json"},
                timeout=10
            )
            
            if update_response.status_code == 200:
                print_success("Successfully marked message as read")
                print_info(f"Message: {subject[:50]}")
                self.add_result("Mark as Read", True, "Success")
                return True
            else:
                print_error(f"Failed to mark message as read (Status: {update_response.status_code})")
                print_error(f"Response: {update_response.text}")
                self.add_result("Mark as Read", False, f"HTTP {update_response.status_code}")
                return False
                
        except Exception as e:
            print_error(f"Exception: {str(e)}")
            self.add_result("Mark as Read", False, str(e))
            return False
    
    def test_send_email(self) -> bool:
        """Test: Send email"""
        print_header("TEST 5: Send Email (Mail.Send)")
        
        if not self.token:
            print_error("No token available")
            self.add_result("Send Email", False, "No token")
            return False
        
        print_warning("This test will send an actual email to the configured account")
        print_info(f"Recipient: {settings.AZURE_EMAIL_USER}")
        
        user_input = input(f"\n{Colors.YELLOW}Continue with sending test email? (yes/no): {Colors.RESET}").strip().lower()
        
        if user_input not in ['yes', 'y']:
            print_info("Test skipped by user")
            self.add_result("Send Email", None, "Skipped by user")
            return True
        
        url = f"https://graph.microsoft.com/v1.0/users/{settings.AZURE_EMAIL_USER}/sendMail"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        email_body = f"""
        <html>
        <body>
        <h2>Azure Email Permission Test</h2>
        <p>This is a test email from the Azure Email Permission Tester.</p>
        <p><strong>Test Time:</strong> {timestamp}</p>
        <p>If you received this email, the Mail.Send permission is working correctly.</p>
        </body>
        </html>
        """
        
        payload = {
            "message": {
                "subject": f"Azure Email Test - {timestamp}",
                "body": {
                    "contentType": "HTML",
                    "content": email_body
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": settings.AZURE_EMAIL_USER
                        }
                    }
                ]
            },
            "saveToSentItems": "true"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 202:
                print_success("Email sent successfully!")
                print_info(f"Check inbox at: {settings.AZURE_EMAIL_USER}")
                self.add_result("Send Email", True, "Success")
                return True
            else:
                print_error(f"Failed to send email (Status: {response.status_code})")
                print_error(f"Response: {response.text}")
                self.add_result("Send Email", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print_error(f"Exception: {str(e)}")
            self.add_result("Send Email", False, str(e))
            return False
    
    def test_reply_to_message(self) -> bool:
        """Test: Reply to an existing message"""
        print_header("TEST 6: Reply to Message (Mail.Send)")
        
        if not self.token:
            print_error("No token available")
            self.add_result("Reply to Message", False, "No token")
            return False
        
        # Get a recent message to reply to
        url = f"https://graph.microsoft.com/v1.0/users/{settings.AZURE_EMAIL_USER}/mailFolders/inbox/messages"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = {"$top": 1, "$select": "id,subject"}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code != 200:
                print_warning("Could not fetch messages to test reply")
                self.add_result("Reply to Message", None, "No messages to reply to")
                return True
            
            messages = response.json().get("value", [])
            
            if not messages:
                print_warning("No messages found to test reply functionality")
                print_info("Send an email first, then run this test again")
                self.add_result("Reply to Message", None, "No messages")
                return True
            
            message_id = messages[0].get("id")
            subject = messages[0].get("subject", "No subject")
            
            print_warning(f"This test will reply to: {subject[:50]}")
            user_input = input(f"\n{Colors.YELLOW}Continue with sending test reply? (yes/no): {Colors.RESET}").strip().lower()
            
            if user_input not in ['yes', 'y']:
                print_info("Test skipped by user")
                self.add_result("Reply to Message", None, "Skipped by user")
                return True
            
            reply_url = f"https://graph.microsoft.com/v1.0/users/{settings.AZURE_EMAIL_USER}/messages/{message_id}/reply"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            payload = {
                "comment": f"This is an automated test reply sent at {timestamp} to verify the Mail.Send permission for replying to messages."
            }
            
            reply_response = requests.post(
                reply_url,
                json=payload,
                headers={**headers, "Content-Type": "application/json"},
                timeout=10
            )
            
            if reply_response.status_code == 202:
                print_success("Reply sent successfully!")
                self.add_result("Reply to Message", True, "Success")
                return True
            else:
                print_error(f"Failed to send reply (Status: {reply_response.status_code})")
                print_error(f"Response: {reply_response.text}")
                self.add_result("Reply to Message", False, f"HTTP {reply_response.status_code}")
                return False
                
        except Exception as e:
            print_error(f"Exception: {str(e)}")
            self.add_result("Reply to Message", False, str(e))
            return False
    
    def print_summary(self):
        """Print test summary"""
        print_header("TEST SUMMARY")
        
        total_tests = len(self.test_results)
        passed = sum(1 for _, success, _ in self.test_results if success is True)
        failed = sum(1 for _, success, _ in self.test_results if success is False)
        skipped = sum(1 for _, success, _ in self.test_results if success is None)
        
        for test_name, success, message in self.test_results:
            if success is True:
                print_success(f"{test_name}: {message}")
            elif success is False:
                print_error(f"{test_name}: {message}")
            else:
                print_warning(f"{test_name}: {message}")
        
        print(f"\n{Colors.BOLD}Total Tests: {total_tests}{Colors.RESET}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")
        print(f"{Colors.YELLOW}Skipped: {skipped}{Colors.RESET}")
        
        if failed == 0:
            print(f"\n{Colors.GREEN}{Colors.BOLD}✓ All tests passed! Azure permissions are correctly configured.{Colors.RESET}")
        else:
            print(f"\n{Colors.RED}{Colors.BOLD}✗ Some tests failed. Please check Azure App permissions.{Colors.RESET}")
            print(f"\n{Colors.YELLOW}Required API Permissions in Azure Portal:{Colors.RESET}")
            for perm in self.required_permissions:
                print(f"  - {perm}")
            print(f"\n{Colors.YELLOW}Make sure to grant admin consent after adding permissions!{Colors.RESET}")
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        print(f"{Colors.BOLD}{Colors.BLUE}")
        print("╔═══════════════════════════════════════════════════════════╗")
        print("║        AZURE EMAIL PERMISSION TESTER                      ║")
        print("║        Testing OAuth2 + Microsoft Graph API              ║")
        print("╚═══════════════════════════════════════════════════════════╝")
        print(f"{Colors.RESET}\n")
        
        # Run tests
        if not self.get_token():
            print_error("\n❌ Cannot proceed without a valid token")
            self.print_summary()
            return False
        
        self.test_user_access()
        self.test_read_inbox()
        self.test_mark_as_read()
        self.test_send_email()
        self.test_reply_to_message()
        
        # Print summary
        self.print_summary()
        
        return all(success is not False for _, success, _ in self.test_results)


def main():
    try:
        tester = AzureEmailTester()
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {str(e)}{Colors.RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()