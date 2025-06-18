"""
Simple WebAuthn Credential Test

Direct import test using importlib to bypass module import issues.
"""

import os
import sys
import importlib.util
from pathlib import Path

print("🔍 Testing WebAuthn credential loading with direct import...")

# Get the credential manager file path
okta_path = str(Path(__file__).parent.parent / "okta_login")
credential_manager_path = okta_path + "/authentication/credential_manager.py"

print(f"📂 Credential manager path: {credential_manager_path}")

try:
    # Direct import using importlib
    spec = importlib.util.spec_from_file_location("credential_manager", credential_manager_path)
    credential_manager = importlib.util.module_from_spec(spec)
    
    # Add okta_login to sys.path for dependencies
    sys.path.insert(0, okta_path)
    
    spec.loader.exec_module(credential_manager)
    
    load_webauthn_credential = credential_manager.load_webauthn_credential
    print("✅ Successfully imported load_webauthn_credential via importlib")
    
    # Test credential loading
    rp_id = "postman.okta.com"
    user_identifier = "jared.boynton@postman.com"
    
    print(f"🔑 Loading credential for {user_identifier}@{rp_id}")
    
    credential = load_webauthn_credential(rp_id, user_identifier)
    
    if credential:
        print("✅ WebAuthn credential loaded successfully!")
        print(f"👤 User: {credential.user_name}")
        print(f"🌐 RP ID: {credential.rp_id}")
        print(f"🔑 Credential ID: {credential.credential_id[:16]}...")
        print(f"🔐 Has private key: {bool(credential.private_key)}")
        print(f"👥 User handle: {credential.user_handle}")
        print(f"📊 Sign count: {credential.sign_count}")
        
        print("\n🎉 WebAuthn credential is working correctly!")
        print("✅ Ready for _godcapture integration")
        
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
