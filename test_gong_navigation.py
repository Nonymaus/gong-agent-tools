"""
Test Gong Navigation with Enhanced Debugging

This script tests just the navigation to Gong from Okta app catalog
with comprehensive debugging to identify why navigation is failing.
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


async def test_gong_navigation():
    """Test Gong navigation with enhanced debugging"""
    logger.info("🚀 Testing Gong navigation with enhanced debugging")
    
    try:
        # Import the session extractor
        from authentication.session_extractor import GongSessionExtractor
        
        logger.info("✅ Successfully imported GongSessionExtractor")
        
        # Initialize extractor with headed mode for debugging
        extractor = GongSessionExtractor(headless=False, session_timeout=120)
        
        logger.info("🔄 Starting session capture with navigation debugging...")
        logger.info("📋 This will show detailed debugging of the navigation process")
        
        # Capture fresh session - this will now include enhanced debugging
        session_data = await extractor.capture_fresh_session(target_app="Gong")
        
        if session_data:
            logger.info("✅ Navigation and session capture successful!")
            logger.info(f"👤 User: {session_data.get('user_email', 'Unknown')}")
            logger.info(f"🏢 Cell: {session_data.get('cell_id', 'Unknown')}")
            logger.info(f"🔑 Tokens: {len(session_data.get('authentication_tokens', []))}")
            return True
        else:
            logger.error("❌ Navigation or session capture failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Navigation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("GONG NAVIGATION DEBUG TEST")
    logger.info("=" * 60)
    
    try:
        result = asyncio.run(test_gong_navigation())
        logger.info(f"Navigation Test Result: {'✅ PASSED' if result else '❌ FAILED'}")
    except Exception as e:
        logger.error(f"Test Exception: {e}")
        result = False
    
    if result:
        logger.info("🎉 Navigation is working! Ready for production validation.")
    else:
        logger.info("🔧 Navigation needs debugging - check the detailed output above")
    
    return result


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
