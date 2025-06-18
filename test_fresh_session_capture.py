"""
Test Fresh Gong Session Capture

This script tests the _godcapture integration to capture a fresh Gong session
and validate that it contains all required authentication artifacts.

Usage:
    python test_fresh_session_capture.py
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from agent import GongAgent, GongAgentError
from authentication.session_extractor import GongSessionManager, GongSessionExtractor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_session_capture():
    """Test fresh session capture using _godcapture integration"""
    logger.info("🚀 Testing Gong fresh session capture with _godcapture integration")
    
    try:
        # Initialize session manager
        session_manager = GongSessionManager()
        
        logger.info("🔄 Attempting to capture fresh Gong session...")
        logger.info("📋 This will launch a browser and navigate through Okta authentication")
        logger.info("⚠️ Manual interaction may be required for WebAuthn authentication")
        
        # Capture fresh session
        session_data = await session_manager.get_fresh_session(target_app="Gong")
        
        if not session_data:
            logger.error("❌ Failed to capture session data")
            return False
        
        # Validate session data
        logger.info("✅ Session captured successfully!")
        logger.info(f"👤 User: {session_data.get('user_email', 'Unknown')}")
        logger.info(f"🏢 Cell: {session_data.get('cell_id', 'Unknown')}")
        logger.info(f"🔑 Tokens: {len(session_data.get('authentication_tokens', []))}")
        logger.info(f"🍪 Cookies: {len(session_data.get('session_cookies', {}))}")
        logger.info(f"📂 HAR File: {session_data.get('har_file_path', 'Unknown')}")
        
        # Test session with GongAgent
        logger.info("🔧 Testing session with GongAgent...")
        
        agent = GongAgent()
        
        # Set the fresh session in the agent
        await agent.capture_fresh_session_async(target_app="Gong")
        
        # Test connection
        connection_result = agent.test_connection()
        logger.info(f"🌐 Connection test: {connection_result}")
        
        if connection_result.get('connected', False):
            logger.info("✅ Fresh session is working with GongAgent!")
            
            # Try a simple data extraction to validate
            try:
                logger.info("📞 Testing call data extraction...")
                calls = agent.extract_calls(limit=5)
                logger.info(f"✅ Successfully extracted {len(calls)} calls")
                
                logger.info("👥 Testing user data extraction...")
                users = agent.extract_users()
                logger.info(f"✅ Successfully extracted {len(users)} users")
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Data extraction test failed: {e}")
                return False
        else:
            logger.error(f"❌ Connection test failed: {connection_result.get('error_message', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Session capture test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_session_capture_sync():
    """Synchronous wrapper for session capture test"""
    try:
        return asyncio.run(test_session_capture())
    except Exception as e:
        logger.error(f"❌ Async test failed: {e}")
        return False


async def test_session_extractor_direct():
    """Test session extractor directly"""
    logger.info("🔧 Testing GongSessionExtractor directly...")
    
    try:
        extractor = GongSessionExtractor(headless=False)  # Use headed mode for debugging
        
        session_data = await extractor.capture_fresh_session(target_app="Gong")
        
        if session_data:
            logger.info("✅ Direct session extractor test passed!")
            logger.info(f"Session data keys: {list(session_data.keys())}")
            return True
        else:
            logger.error("❌ Direct session extractor test failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Direct session extractor test failed: {e}")
        return False


def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("GONG FRESH SESSION CAPTURE TEST")
    logger.info("=" * 60)
    
    # Test 1: Direct session extractor test
    logger.info("\n🧪 Test 1: Direct Session Extractor")
    try:
        result1 = asyncio.run(test_session_extractor_direct())
        logger.info(f"Test 1 Result: {'✅ PASSED' if result1 else '❌ FAILED'}")
    except Exception as e:
        logger.error(f"Test 1 Exception: {e}")
        result1 = False
    
    # Test 2: Full integration test
    logger.info("\n🧪 Test 2: Full Integration Test")
    try:
        result2 = test_session_capture_sync()
        logger.info(f"Test 2 Result: {'✅ PASSED' if result2 else '❌ FAILED'}")
    except Exception as e:
        logger.error(f"Test 2 Exception: {e}")
        result2 = False
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Direct Session Extractor: {'✅ PASSED' if result1 else '❌ FAILED'}")
    logger.info(f"Full Integration Test: {'✅ PASSED' if result2 else '❌ FAILED'}")
    
    overall_success = result1 and result2
    logger.info(f"Overall Result: {'✅ ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
    
    if overall_success:
        logger.info("🎉 Fresh session capture is working! Ready for production validation.")
    else:
        logger.info("🔧 Fresh session capture needs debugging before production validation.")
    
    return overall_success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
