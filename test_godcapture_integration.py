"""
Module: test_godcapture_integration
Type: Test

Purpose:
Unit tests for Gong functionality ensuring reliability and correctness.

Data Flow:
- Input: Configuration parameters, Authentication credentials
- Processing: Input validation, Data extraction
- Output: Error states and exceptions

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: asyncio, logging, authentication.session_extractor, authentication.session_extractor, traceback
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_godcapture_session_capture():
    """Test _godcapture session capture directly"""
    logger.info("🚀 Testing _godcapture session capture for Gong")
    
    try:
        # Import the session extractor
        from authentication.session_extractor import GongSessionExtractor
        
        logger.info("✅ Successfully imported GongSessionExtractor")
        
        # Initialize extractor with headed mode for debugging
        extractor = GongSessionExtractor(headless=False, session_timeout=300)
        
        logger.info("🔄 Starting fresh session capture...")
        logger.info("📋 This will launch a browser and navigate through Okta authentication")
        logger.info("⚠️ Manual interaction may be required")
        
        # Capture fresh session
        session_data = await extractor.capture_fresh_session(target_app="Gong")
        
        if session_data:
            logger.info("✅ Session capture successful!")
            logger.info(f"👤 User: {session_data.get('user_email', 'Unknown')}")
            logger.info(f"🏢 Cell: {session_data.get('cell_id', 'Unknown')}")
            logger.info(f"🔑 Tokens: {len(session_data.get('authentication_tokens', []))}")
            logger.info(f"🍪 Cookies: {len(session_data.get('session_cookies', {}))}")
            logger.info(f"📂 HAR File: {session_data.get('har_file_path', 'Unknown')}")
            
            # Validate session data
            tokens = session_data.get('authentication_tokens', [])
            valid_tokens = [t for t in tokens if not t.get('is_expired', True)]
            
            if valid_tokens:
                logger.info(f"✅ Found {len(valid_tokens)} valid authentication tokens")
                return True
            else:
                logger.error("❌ No valid authentication tokens found")
                return False
        else:
            logger.error("❌ Session capture failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Session capture test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_session_manager():
    """Test the GongSessionManager"""
    logger.info("🔧 Testing GongSessionManager...")
    
    try:
        from authentication.session_extractor import GongSessionManager
        
        session_manager = GongSessionManager()
        logger.info("✅ GongSessionManager initialized")
        
        # Test fresh session capture
        session_data = await session_manager.get_fresh_session(target_app="Gong")
        
        if session_data:
            logger.info("✅ Session manager test passed!")
            return True
        else:
            logger.error("❌ Session manager test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Session manager test failed: {e}")
        return False


def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("GONG _GODCAPTURE INTEGRATION TEST")
    logger.info("=" * 60)
    
    # Test 1: Direct session extractor
    logger.info("\n🧪 Test 1: Direct Session Extractor")
    try:
        result1 = asyncio.run(test_godcapture_session_capture())
        logger.info(f"Test 1 Result: {'✅ PASSED' if result1 else '❌ FAILED'}")
    except Exception as e:
        logger.error(f"Test 1 Exception: {e}")
        result1 = False
    
    # Test 2: Session Manager
    logger.info("\n🧪 Test 2: Session Manager")
    try:
        result2 = asyncio.run(test_session_manager())
        logger.info(f"Test 2 Result: {'✅ PASSED' if result2 else '❌ FAILED'}")
    except Exception as e:
        logger.error(f"Test 2 Exception: {e}")
        result2 = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Direct Session Extractor: {'✅ PASSED' if result1 else '❌ FAILED'}")
    logger.info(f"Session Manager: {'✅ PASSED' if result2 else '❌ FAILED'}")
    
    overall_success = result1 or result2  # At least one should pass
    logger.info(f"Overall Result: {'✅ INTEGRATION WORKING' if overall_success else '❌ INTEGRATION FAILED'}")
    
    if overall_success:
        logger.info("🎉 _godcapture integration is working! Ready for production validation.")
        logger.info("📋 Next step: Run production validation tests with fresh session")
    else:
        logger.info("🔧 _godcapture integration needs debugging")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
