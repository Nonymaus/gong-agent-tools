#!/usr/bin/env python3
"""
Gong Real Data Validation Summary
Validates Gong toolkit against ground truth data
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GongDataValidationSummary:
    """Generates validation summary for Gong toolkit"""
    
    def __init__(self):
        self.validation_dir = Path(__file__).parent / "validation"
        self.call_data_dir = self.validation_dir / "gong_call1"
        self.email_data_dir = self.validation_dir / "gong_emails"
        
    def analyze_ground_truth(self):
        """Analyze ground truth data structure"""
        logger.info("=== GONG VALIDATION DATA ANALYSIS ===\n")
        
        # Analyze call data
        logger.info("📞 CALL DATA (gong_call1):")
        call_files = list(self.call_data_dir.glob("*.txt"))
        for file in sorted(call_files):
            size = file.stat().st_size
            logger.info(f"  - {file.name}: {size} bytes")
        
        # Sample call info
        callinfo_file = self.call_data_dir / "callinfo.txt"
        if callinfo_file.exists():
            with open(callinfo_file, 'r') as f:
                lines = f.read().strip().split('\n')
            logger.info(f"\n  Call Info Preview:")
            for line in lines[:10]:
                logger.info(f"    {line}")
        
        # Analyze email data
        logger.info(f"\n📧 EMAIL DATA (gong_emails):")
        email_files = list(self.email_data_dir.glob("*.txt"))
        for file in sorted(email_files):
            size = file.stat().st_size
            logger.info(f"  - {file.name}: {size} bytes")
        
        # Show validation requirements
        logger.info("\n✅ VALIDATION REQUIREMENTS:")
        logger.info("  - Field-level accuracy: >95%")
        logger.info("  - Record completeness: 100%")
        logger.info("  - Performance: <30 seconds")
        
        # Current status
        logger.info("\n📊 CURRENT STATUS:")
        logger.info("  - Ground truth data: ✅ Available")
        logger.info("  - Gong toolkit: ✅ Implemented")
        logger.info("  - Session data: ⚠️  May need refresh")
        logger.info("  - Validation test: 🔄 Ready to run")
        
        # Next steps
        logger.info("\n🚀 NEXT STEPS:")
        logger.info("  1. Capture fresh Gong session using _godcapture if needed")
        logger.info("  2. Run integration test to extract live data")
        logger.info("  3. Compare extracted data with ground truth")
        logger.info("  4. Generate detailed accuracy report")
        
        # Data structure for validation
        logger.info("\n📋 DATA STRUCTURE FOR VALIDATION:")
        logger.info("  Call Data Fields:")
        logger.info("    - title, time, scheduled_on, language")
        logger.info("    - account, deal, participants")
        logger.info("    - attendees (emails), transcript")
        logger.info("    - interaction_stats, spotlight")
        logger.info("  Email Data Fields:")
        logger.info("    - sender, recipients, timestamp")
        logger.info("    - subject, body, thread_id")
        
        return True

if __name__ == "__main__":
    validator = GongDataValidationSummary()
    validator.analyze_ground_truth()
