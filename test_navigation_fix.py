"""
Test Navigation Fix

Quick test to verify the corrected navigation method works for Gong.
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


async def test_navigation_fix():
    """Test the corrected navigation method"""
    logger.info("🧪 Testing corrected Gong navigation method")
    
    try:
        from authentication.session_extractor import GongSessionExtractor
        
        # Initialize extractor with headed mode for debugging
        extractor = GongSessionExtractor(headless=False, session_timeout=300)
        
        logger.info("🔄 Starting session capture with corrected navigation...")
        
        # Capture fresh session
        session_data = await extractor.capture_fresh_session(target_app="Gong")
        
        if session_data:
            logger.info("✅ Navigation fix successful!")
            logger.info(f"👤 User: {session_data.get('user_email', 'Unknown')}")
            logger.info(f"🏢 Cell: {session_data.get('cell_id', 'Unknown')}")
            logger.info(f"🔑 Tokens: {len(session_data.get('authentication_tokens', []))}")
            
            # Check if we have valid tokens
            tokens = session_data.get('authentication_tokens', [])
            valid_tokens = [t for t in tokens if not t.get('is_expired', True)]
            
            if valid_tokens:
                logger.info(f"✅ Found {len(valid_tokens)} valid authentication tokens")
                logger.info("🎉 Ready for production validation tests!")
                return True
            else:
                logger.warning("⚠️ No valid tokens found, but navigation worked")
                return True
        else:
            logger.error("❌ Session capture failed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Navigation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    logger.info("=" * 60)
    logger.info("GONG NAVIGATION FIX TEST")
    logger.info("=" * 60)
    
    try:
        result = asyncio.run(test_navigation_fix())
        logger.info(f"Test Result: {'✅ PASSED' if result else '❌ FAILED'}")
        
        if result:
            logger.info("🎉 Navigation fix successful! Ready to run production validation.")
        else:
            logger.info("🔧 Navigation still needs debugging.")
        
        return result
        
    except Exception as e:
        logger.error(f"Test Exception: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
