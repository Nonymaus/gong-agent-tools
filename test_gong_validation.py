#!/usr/bin/env python3
"""
Gong Real Data Validation Test
Validates Gong toolkit extraction against ground truth data
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import asyncio

# Add the parent directory to the path so we can import the Gong modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from gong.agent import GongAgent
from gong.api_client import GongAPIClient
from gong.authentication import GongAuthenticationManager
from gong.data_models import *

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GongRealDataValidator:
    """Validates Gong toolkit extraction against ground truth data"""
    
    def __init__(self):
        self.validation_dir = Path(__file__).parent / "validation"
        self.call_data_dir = self.validation_dir / "gong_call1"
        self.email_data_dir = self.validation_dir / "gong_emails"
        
        # Validation metrics
        self.total_fields = 0
        self.matched_fields = 0
        self.mismatches = []
        self.missing_records = []
        
    def parse_call_info(self, content: str) -> Dict[str, Any]:
        """Parse call info from text content"""
        lines = content.strip().split('\n')
        call_info = {}
        
        current_key = None
        current_value = []
        
        key_mappings = {
            'Call title': 'title',
            'Call time': 'time', 
            'Scheduled on': 'scheduled_on',
            'Language': 'language',
            'Account': 'account',
            'Deal': 'deal'
        }
        
        for line in lines:
            line = line.strip()
            
            if line in key_mappings:
                if current_key:
                    call_info[current_key] = '\n'.join(current_value).strip()
                current_key = key_mappings[line]
                current_value = []
            elif current_key and line:
                current_value.append(line)
        
        if current_key:
            call_info[current_key] = '\n'.join(current_value).strip()
        
        return call_info
    
    def load_ground_truth(self) -> Dict[str, Any]:
        """Load all ground truth data"""
        data = {
            'call': {},
            'emails': []
        }
        
        # Load call data
        if self.call_data_dir.exists():
            # Load call info
            callinfo_file = self.call_data_dir / "callinfo.txt"
            if callinfo_file.exists():
                with open(callinfo_file, 'r') as f:
                    data['call']['info'] = self.parse_call_info(f.read())
            
            # Load attendees  
            attendees_file = self.call_data_dir / "attendees.txt"
            if attendees_file.exists():
                with open(attendees_file, 'r') as f:
                    content = f.read().strip()
                    data['call']['attendees'] = [
                        email.strip() for email in content.split(';') if email.strip()
                    ]
        
        return data
    
    async def extract_gong_data(self) -> Dict[str, Any]:
        """Extract data using the Gong toolkit"""
        logger.info("Initializing Gong toolkit...")
        
        try:
            # Initialize the Gong agent
            agent = GongAgent()
            
            # Check if we have a valid session
            session_file = Path(__file__).parent.parent / "_godcapture" / ".godcaptures" / "gong-test" / "session.json"
            
            if not session_file.exists():
                logger.error(f"Session file not found at {session_file}")
                logger.error("Please capture a fresh Gong session using _godcapture")
                return None
            
            # Load session data
            with open(session_file, 'r') as f:
                session_data = json.load(f)
            
            # Initialize API client with session
            api_client = GongAPIClient()
            api_client.session = session_data.get('cookies', {})
            api_client.headers = session_data.get('headers', {})
            
            # Try to extract some data
            logger.info("Attempting to extract calls...")
            
            # For now, return mock data since we need a fresh session
            return {
                'calls': [],
                'conversations': []
            }
            
        except Exception as e:
            logger.error(f"Failed to extract Gong data: {str(e)}")
            return None
    
    def compare_field(self, field_name: str, expected: Any, actual: Any) -> bool:
        """Compare a single field and record the result"""
        self.total_fields += 1
        
        # Normalize for comparison
        if isinstance(expected, str) and isinstance(actual, str):
            expected = expected.strip().lower()
            actual = actual.strip().lower()
        
        if expected == actual:
            self.matched_fields += 1
            return True
        else:
            self.mismatches.append({
                'field': field_name,
                'expected': expected,
                'actual': actual
            })
            return False
    
    def validate_call_data(self, ground_truth: Dict, extracted: Dict) -> float:
        """Validate call data and return accuracy percentage"""
        if not ground_truth.get('call') or not extracted:
            return 0.0
        
        gt_info = ground_truth['call'].get('info', {})
        
        # For now, since we don't have extracted data, return 0
        # In a real scenario, we would compare each field
        
        # Example of how validation would work:
        # self.compare_field('title', gt_info.get('title'), extracted.get('title'))
        # self.compare_field('account', gt_info.get('account'), extracted.get('account'))
        # etc.
        
        return 0.0
    
    async def run_validation(self):
        """Run the complete validation test"""
        logger.info("=== Gong Real Data Validation Test ===")
        
        # Load ground truth
        logger.info("\n1. Loading ground truth data...")
        ground_truth = self.load_ground_truth()
        logger.info(f"   ✓ Loaded call info with {len(ground_truth['call'].get('info', {}))} fields")
        logger.info(f"   ✓ Loaded {len(ground_truth['call'].get('attendees', []))} attendees")
        
        # Extract data using toolkit
        logger.info("\n2. Extracting data using Gong toolkit...")
        extracted_data = await self.extract_gong_data()
        
        if not extracted_data:
            logger.error("   ✗ Failed to extract data - likely need fresh session")
            logger.info("\n📋 NEXT STEPS:")
            logger.info("   1. Capture a fresh Gong session using _godcapture")
            logger.info("   2. Re-run this validation test")
            return False
        
        # Validate the data
        logger.info("\n3. Validating extracted data against ground truth...")
        call_accuracy = self.validate_call_data(ground_truth, extracted_data)
        
        # Calculate overall accuracy
        overall_accuracy = self.matched_fields / self.total_fields if self.total_fields > 0 else 0.0
        
        # Display results
        logger.info("\n=== VALIDATION RESULTS ===")
        logger.info(f"Total Fields Checked: {self.total_fields}")
        logger.info(f"Matched Fields: {self.matched_fields}")
        logger.info(f"Mismatched Fields: {len(self.mismatches)}")
        logger.info(f"Overall Accuracy: {overall_accuracy * 100:.1f}%")
        
        # Show mismatches
        if self.mismatches:
            logger.info("\nField Mismatches:")
            for mismatch in self.mismatches[:5]:  # Show first 5
                logger.info(f"  - {mismatch['field']}")
                logger.info(f"    Expected: {mismatch['expected']}")
                logger.info(f"    Actual: {mismatch['actual']}")
            
            if len(self.mismatches) > 5:
                logger.info(f"  ... and {len(self.mismatches) - 5} more mismatches")
        
        # Check if we meet requirements
        required_accuracy = 0.95
        success = overall_accuracy >= required_accuracy
        
        if success:
            logger.info(f"\n✅ VALIDATION PASSED! Accuracy {overall_accuracy * 100:.1f}% >= {required_accuracy * 100}%")
        else:
            logger.info(f"\n❌ VALIDATION FAILED! Accuracy {overall_accuracy * 100:.1f}% < {required_accuracy * 100}%")
        
        return success

if __name__ == "__main__":
    validator = GongRealDataValidator()
    success = asyncio.run(validator.run_validation())
    sys.exit(0 if success else 1)
