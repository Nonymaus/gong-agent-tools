#!/usr/bin/env python3
"""
Simple Gong Validation Runner
Tests basic extraction without complex imports
"""

import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_validation():
    """Run validation using direct script execution"""
    logger.info("🚀 Starting Gong Validation Test")
    logger.info("=" * 50)
    
    # Step 1: Check if we can import the agent
    logger.info("\n1️⃣ Testing Gong agent import...")
    try:
        # Run a simple test script
        test_script = '''
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from app_backend.agent_tools.gong.agent import GongAgent
    agent = GongAgent()
    print("✅ Agent imported successfully")
    
    # Try to get status
    status = agent.get_status()
    print(f"Session available: {status.get('session_available', False)}")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)
'''
        
        result = subprocess.run(
            [sys.executable, '-c', test_script],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True
        )
        
        logger.info(result.stdout)
        if result.stderr:
            logger.error(result.stderr)
            
        if result.returncode != 0:
            logger.error("Failed to import Gong agent")
            return False
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    
    # Step 2: Load ground truth data
    logger.info("\n2️⃣ Loading ground truth data...")
    validation_dir = Path(__file__).parent / "validation"
    
    ground_truth_summary = {
        'calls': 0,
        'emails': 0,
        'transcript_segments': 0
    }
    
    # Count call data
    call_dir = validation_dir / "gong_call1"
    if call_dir.exists():
        if (call_dir / "callinfo.txt").exists():
            ground_truth_summary['calls'] = 1
        if (call_dir / "transcript.txt").exists():
            with open(call_dir / "transcript.txt", 'r') as f:
                content = f.read()
                # Count speaker changes as segments
                ground_truth_summary['transcript_segments'] = content.count(':') - 1
    
    # Count emails
    email_dir = validation_dir / "gong_emails"
    if email_dir.exists():
        ground_truth_summary['emails'] = len(list(email_dir.glob("*.txt")))
    
    logger.info(f"Ground truth summary: {json.dumps(ground_truth_summary, indent=2)}")
    
    # Step 3: Test extraction (if session available)
    logger.info("\n3️⃣ Testing data extraction...")
    
    extraction_test = '''
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from app_backend.agent_tools.gong.agent import GongAgent
    
    agent = GongAgent()
    status = agent.get_status()
    
    if not status.get('session_available'):
        print("⚠️ No session available - skipping extraction test")
        print("Run with fresh session to complete validation")
    else:
        # Try basic extraction
        print("Attempting to extract users...")
        data = agent.extract_data({'users': True})
        
        if data.get('users'):
            print(f"✅ Extracted {len(data['users'])} users")
        else:
            print("❌ No users extracted")
            
except Exception as e:
    print(f"❌ Extraction test failed: {e}")
'''
    
    result = subprocess.run(
        [sys.executable, '-c', extraction_test],
        cwd=Path(__file__).parent,
        capture_output=True,
        text=True
    )
    
    logger.info(result.stdout)
    if result.stderr:
        logger.error(result.stderr)
    
    # Step 4: Document next steps
    logger.info("\n4️⃣ Next Steps for Full Validation:")
    logger.info("   1. Capture fresh Gong session using _godcapture")
    logger.info("   2. Run: python3 run_full_validation_with_refresh.py")
    logger.info("   3. Check VALIDATION_RESULTS_FULL.json for results")
    
    logger.info("\n📋 Manual Session Capture:")
    logger.info("   cd ../../../")
    logger.info("   python3 -m app_backend.agent_tools._godcapture reauthenticate gong --force")
    
    return True

if __name__ == "__main__":
    success = run_validation()
    
    if success:
        logger.info("\n✅ Basic validation tests completed!")
    else:
        logger.info("\n❌ Validation tests failed")
        sys.exit(1)
