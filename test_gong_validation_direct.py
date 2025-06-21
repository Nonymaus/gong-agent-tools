#!/usr/bin/env python3
"""
Direct Gong Validation Test
No complex imports - just test what we have
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Set up paths properly
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir.parent))
sys.path.insert(0, str(current_dir.parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_gong_validation():
    """Test Gong validation directly"""
    
    logger.info("🚀 Gong Validation Test")
    logger.info("=" * 50)
    
    # Step 1: Check ground truth data
    logger.info("\n1️⃣ Checking ground truth data...")
    
    validation_dir = current_dir / "validation"
    if not validation_dir.exists():
        logger.error(f"❌ Validation directory not found: {validation_dir}")
        return False
        
    # Check call data
    call_dir = validation_dir / "gong_call1"
    call_files = {
        'callinfo.txt': False,
        'attendees.txt': False,
        'transcript.txt': False,
        'interactionstats.txt': False,
        'spotlight.txt': False
    }
    
    for filename in call_files:
        filepath = call_dir / filename
        if filepath.exists():
            call_files[filename] = True
            size = filepath.stat().st_size
            logger.info(f"  ✅ {filename}: {size} bytes")
        else:
            logger.info(f"  ❌ {filename}: not found")
    
    # Check email data
    email_dir = validation_dir / "gong_emails"
    email_count = 0
    if email_dir.exists():
        email_files = list(email_dir.glob("*.txt"))
        email_count = len(email_files)
        logger.info(f"\n  📧 Found {email_count} email files")
        for email_file in email_files[:3]:  # Show first 3
            logger.info(f"    - {email_file.name}")
        if email_count > 3:
            logger.info(f"    ... and {email_count - 3} more")
    
    # Step 2: Try to import and check session
    logger.info("\n2️⃣ Testing Gong agent...")
    
    try:
        # Direct import
        import agent
        gong_agent = agent.GongAgent()
        logger.info("  ✅ GongAgent imported successfully")
        
        # Check status
        status = gong_agent.get_status()
        logger.info(f"  📊 Agent Status:")
        logger.info(f"    - Session available: {status.get('session_available', False)}")
        logger.info(f"    - Session valid: {status.get('session_valid', False)}")
        logger.info(f"    - Authentication type: {status.get('authentication_type', 'Unknown')}")
        
        if status.get('last_activity'):
            logger.info(f"    - Last activity: {status['last_activity']}")
        
    except Exception as e:
        logger.error(f"  ❌ Failed to import agent: {e}")
        logger.info("\n  💡 Trying alternative approach...")
        
        # Try running the existing validation script
        try:
            import run_gong_validation
            validator = run_gong_validation.GongDataValidator()
            ground_truth = validator.run_validation()
            logger.info("  ✅ Ground truth validation successful")
            
        except Exception as e2:
            logger.error(f"  ❌ Alternative approach failed: {e2}")
            return False
    
    # Step 3: Summary and next steps
    logger.info("\n3️⃣ Validation Summary:")
    logger.info(f"  - Ground truth files: {sum(call_files.values())}/5 call files, {email_count} emails")
    logger.info("  - Agent status: Check complete")
    
    logger.info("\n4️⃣ To complete full validation:")
    logger.info("  1. Ensure fresh Gong session is captured")
    logger.info("  2. Run the agent's extract_data() method")
    logger.info("  3. Compare extracted data with ground truth")
    logger.info("  4. Calculate accuracy metrics")
    
    logger.info("\n📝 Quick session refresh command:")
    logger.info("  cd " + str(current_dir.parent.parent.parent))
    logger.info("  python3 -m app_backend.agent_tools._godcapture.core.__main__ reauthenticate gong")
    
    return True

if __name__ == "__main__":
    success = test_gong_validation()
    
    if success:
        logger.info("\n✅ Validation check completed!")
    else:
        logger.info("\n❌ Validation check failed")
        sys.exit(1)
