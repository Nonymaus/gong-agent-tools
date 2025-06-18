"""
Test WebAuthn Credential Loading

This script tests if the WebAuthn credential is properly loaded from the .env file
using the okta_login credential manager.
"""

import os
import sys
from pathlib import Path

# Add okta_login to path
okta_path = str(Path(__file__).parent.parent / "okta_login")
sys.path.insert(0, okta_path)

print(f"🔍 Testing WebAuthn credential loading...")
print(f"📂 Okta path: {okta_path}")

try:
    # Change to okta_login directory temporarily for import
    original_cwd = os.getcwd()
    os.chdir(okta_path)

    try:
        from authentication.credential_manager import load_webauthn_credential
        print("✅ Successfully imported load_webauthn_credential")
    finally:
        # Restore original directory
        os.chdir(original_cwd)

except ImportError as e:
    print(f"❌ Failed to import load_webauthn_credential: {e}")
    sys.exit(1)

# Test credential loading
rp_id = "postman.okta.com"
user_identifier = "jared.boynton@postman.com"

print(f"🔑 Loading credential for {user_identifier}@{rp_id}")

try:
    credential = load_webauthn_credential(rp_id, user_identifier)
    
    if credential:
        print("✅ WebAuthn credential loaded successfully!")
        print(f"👤 User: {credential.user_name}")
        print(f"🌐 RP ID: {credential.rp_id}")
        print(f"🔑 Credential ID: {credential.credential_id[:16]}...")
        print(f"🔐 Has private key: {bool(credential.private_key)}")
        print(f"👥 User handle: {credential.user_handle}")
        print(f"📊 Sign count: {credential.sign_count}")
    else:
        print("❌ No WebAuthn credential found")
        
        # Check if environment variable exists
        env_key = f"WEBAUTHN_CREDENTIAL_{rp_id.upper().replace('.', '_')}_{user_identifier.upper().replace('@', '_AT_').replace('.', '_')}"
        print(f"🔍 Looking for env var: {env_key}")
        
        env_value = os.getenv(env_key)
        if env_value:
            print(f"✅ Environment variable exists (length: {len(env_value)})")
        else:
            print("❌ Environment variable not found")
            
            # List all WEBAUTHN env vars
            webauthn_vars = [k for k in os.environ.keys() if k.startswith('WEBAUTHN_')]
            print(f"🔍 Available WEBAUTHN env vars: {webauthn_vars}")
        
except Exception as e:
    print(f"❌ Error loading credential: {e}")
    import traceback
    traceback.print_exc()
