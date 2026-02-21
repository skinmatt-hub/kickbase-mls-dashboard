"""
Full Authentication Manager for Kickbase API
Handles login, token refresh, and automatic re-authentication
"""
import requests
import json
from datetime import datetime
from pathlib import Path
import re

BASE_URL = "https://api.kickbase.com/v4"
LOGIN_ENDPOINT = f"{BASE_URL}/user/login"
CONFIG_FILE = Path(__file__).parent / "config.py"

class KickbaseAuthManager:
    """Manages Kickbase authentication with automatic refresh"""
    
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.chat_token = None
    
    def login(self):
        """
        Login with email and password to get tokens
        
        Returns:
            dict: Token information or None if failed
        """
        print(f"🔐 Logging in as {self.email}...")
        
        try:
            response = requests.post(
                LOGIN_ENDPOINT,
                json={
                    "em": self.email,
                    "pass": self.password,
                    "ext": True,
                    "loy": False,
                    "rep": {}
                },
                headers={
                    "Content-Type": "application/json",
                    "KB-Store-Region": "USA",
                    "KB-Region": "US",
                    "Accept": "*/*"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                
                self.token = data.get('tkn')
                self.refresh_token = data.get('rtkn')
                self.chat_token = data.get('chttkn')
                
                # Parse expiration
                token_expires_str = data.get('tknex')
                if token_expires_str:
                    try:
                        self.token_expires_at = datetime.fromisoformat(
                            token_expires_str.replace('Z', '+00:00')
                        )
                    except:
                        # Fallback: assume 1 hour from now
                        from datetime import timedelta
                        self.token_expires_at = datetime.now() + timedelta(hours=1)
                
                print(f"✅ Login successful!")
                print(f"   Token: {self.token[:50] if self.token else 'None'}...")
                if self.refresh_token:
                    print(f"   Refresh Token: {self.refresh_token[:30]}...")
                print(f"   Expires: {self.token_expires_at}")
                
                return {
                    'token': self.token,
                    'refresh_token': self.refresh_token,
                    'expires_at': self.token_expires_at,
                    'user': data.get('u', {}),
                    'leagues': data.get('lins', [])
                }
            else:
                print(f"❌ Login failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Login error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def is_token_expired(self):
        """Check if current token is expired or about to expire"""
        if not self.token_expires_at:
            return True
        
        time_left = (self.token_expires_at - datetime.now()).total_seconds()
        # Refresh if less than 5 minutes left
        return time_left < 300
    
    def get_valid_token(self):
        """
        Get a valid token, refreshing if necessary
        
        Returns:
            str: Valid token or None if failed
        """
        # If no token or expired, login
        if not self.token or self.is_token_expired():
            print("🔄 Token expired or missing, logging in...")
            result = self.login()
            if result:
                return self.token
            else:
                return None
        
        return self.token


def login_and_save(email, password):
    """
    Login and save tokens to config file
    
    Args:
        email: User email
        password: User password
        
    Returns:
        dict: Login result or None if failed
    """
    auth = KickbaseAuthManager(email, password)
    result = auth.login()
    
    if result:
        # Update config file
        update_config_file(
            result['token'],
            result['refresh_token']
        )
        return result
    
    return None


def update_config_file(token, refresh_token=None):
    """
    Update config.py with new tokens
    
    Args:
        token: New API token
        refresh_token: New refresh token (optional)
        
    Returns:
        bool: True if successful
    """
    try:
        # Read current config
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        # Update token
        pattern = r'KICKBASE_TOKEN = "([^"]+)"'
        if re.search(pattern, config_content):
            config_content = re.sub(
                pattern,
                f'KICKBASE_TOKEN = "{token}"',
                config_content
            )
        else:
            print("⚠️ Could not find KICKBASE_TOKEN in config")
            return False
        
        # Add or update refresh token
        if refresh_token:
            refresh_pattern = r'REFRESH_TOKEN = "([^"]+)"'
            if re.search(refresh_pattern, config_content):
                config_content = re.sub(
                    refresh_pattern,
                    f'REFRESH_TOKEN = "{refresh_token}"',
                    config_content
                )
            else:
                # Add refresh token after KICKBASE_TOKEN
                config_content = config_content.replace(
                    f'KICKBASE_TOKEN = "{token}"',
                    f'KICKBASE_TOKEN = "{token}"\nREFRESH_TOKEN = "{refresh_token}"'
                )
        
        # Write back
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        print("✅ Config file updated")
        return True
        
    except Exception as e:
        print(f"❌ Error updating config: {e}")
        return False


if __name__ == "__main__":
    # Test authentication
    print("="*70)
    print("KICKBASE AUTHENTICATION MANAGER TEST")
    print("="*70)
    
    EMAIL = "skinsstar06@gmail.com"
    PASSWORD = "Messi101996$"
    
    # Test login
    result = login_and_save(EMAIL, PASSWORD)
    
    if result:
        print("\n" + "="*70)
        print("✅ AUTHENTICATION SUCCESSFUL!")
        print("="*70)
        print(f"\n👤 User: {result['user'].get('name')}")
        print(f"📧 Email: {result['user'].get('email')}")
        print(f"🏆 Leagues: {len(result['leagues'])}")
        for league in result['leagues']:
            print(f"   - {league.get('n')}")
        print(f"\n🔑 Token saved to config.py")
        print(f"⏰ Expires: {result['expires_at']}")
        
        # Test API call with new token
        print("\n" + "="*70)
        print("TESTING API WITH NEW TOKEN")
        print("="*70)
        
        response = requests.get(
            f"{BASE_URL}/leagues",
            headers={"Authorization": f"Bearer {result['token']}"}
        )
        
        if response.status_code == 200:
            print("✅ API call successful!")
            print(f"   Leagues endpoint working")
        else:
            print(f"❌ API call failed: {response.status_code}")
    else:
        print("\n❌ Authentication failed")
