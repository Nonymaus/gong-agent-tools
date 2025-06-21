#!/usr/bin/env python3
"""
Complete Gong Validation Script
Runs full validation with automatic session refresh
Shadow architect style - gets shit done
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our tools
try:
    from agent import GongAgent
    from run_gong_validation import GongDataValidator
except ImportError:
    # Try alternative import paths
    from gong.agent import GongAgent
    from gong.run_gong_validation import GongDataValidator

class GongFullValidator:
    """Full validation with session refresh"""
    
    def __init__(self):
        self.agent = GongAgent()
        self.validator = GongDataValidator()
        
    async def ensure_fresh_session(self):
        """Ensure we have a fresh session using godcapture"""
        logger.info("🔐 Checking Gong session...")
        
        # First try using existing session
        try:
            # Simple test call to see if session works
            test_data = await self.agent.extract_data({'users': True})
            if test_data.get('users'):
                logger.info("✅ Existing session is valid")
                return True
        except Exception as e:
            logger.info(f"❌ Session invalid or expired: {e}")
        
        # Need to refresh session
        logger.info("🔄 Refreshing session via GodCapture...")
        
        try:
            # Import godcapture
            from _godcapture.core.godcapture import GodCapture
            from _godcapture.adapters.base_services_adapter import BaseServicesAdapter
            from _godcapture.adapters.okta_login_adapter import OktaLoginAdapter
            
            # Initialize godcapture
            base_services = BaseServicesAdapter()
            okta_login = OktaLoginAdapter()
            godcapture = GodCapture(base_services, okta_login)
            
            # Reauthenticate for Gong
            session_data = await godcapture.reauthenticate('gong', force=True)
            
            if session_data and session_data.is_valid():
                logger.info("✅ Fresh session captured successfully")
                return True
            else:
                logger.error("❌ Failed to capture fresh session")
                return False
                
        except ImportError as e:
            logger.warning(f"⚠️ GodCapture import failed: {e}")
            logger.info("Falling back to manual session refresh...")
            
            # Alternative: Use the agent's built-in refresh
            # This might require manual browser interaction
            logger.info("Please manually refresh your Gong session in the browser")
            logger.info("Then press Enter to continue...")
            input()
            return True
            
    def extract_gong_data(self):
        """Extract data from Gong matching our ground truth types"""
        logger.info("\n📊 Extracting Gong data...")
        
        try:
            # Extract all data types we need for validation
            config = {
                'calls': True,
                'users': True,
                'conversations': True,
                'library': True,
                'team_stats': True
            }
            
            extracted = self.agent.extract_data(config)
            
            # Log what we got
            logger.info("\nExtraction Results:")
            for data_type, data in extracted.items():
                if isinstance(data, list):
                    logger.info(f"  - {data_type}: {len(data)} items")
                elif data:
                    logger.info(f"  - {data_type}: ✓")
                else:
                    logger.info(f"  - {data_type}: ✗")
            
            return extracted
            
        except Exception as e:
            logger.error(f"❌ Extraction failed: {e}")
            return None
            
    def compare_with_ground_truth(self, extracted_data, ground_truth):
        """Compare extracted data with ground truth"""
        logger.info("\n🔍 Validating against ground truth...")
        
        validation_results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        
        # Validate call data
        if ground_truth['call'].get('info'):
            logger.info("\n📞 Validating Call Data:")
            call_info = ground_truth['call']['info']
            
            # Find matching call in extracted data
            extracted_calls = extracted_data.get('calls', [])
            matching_call = None
            
            for call in extracted_calls:
                # Match by title or time
                if (call.get('title') == call_info.get('title') or 
                    call.get('scheduled_time') == call_info.get('scheduled_on')):
                    matching_call = call
                    break
            
            if matching_call:
                logger.info("  ✅ Found matching call")
                validation_results['passed'].append('call_found')
                
                # Validate participants
                if call_info.get('participants'):
                    gt_participants = call_info['participants']
                    ext_participants = matching_call.get('participants', [])
                    
                    # Count participants by company
                    gt_postman = len(gt_participants.get('postman', []))
                    gt_salesforce = len(gt_participants.get('salesforce', []))
                    
                    ext_postman = sum(1 for p in ext_participants 
                                     if 'postman' in p.get('email', '').lower())
                    ext_salesforce = sum(1 for p in ext_participants 
                                        if 'salesforce' in p.get('email', '').lower())
                    
                    if ext_postman >= gt_postman * 0.8:  # 80% threshold
                        logger.info(f"  ✅ Postman participants match ({ext_postman}/{gt_postman})")
                        validation_results['passed'].append('postman_participants')
                    else:
                        logger.info(f"  ❌ Postman participants mismatch ({ext_postman}/{gt_postman})")
                        validation_results['failed'].append('postman_participants')
                        
                    if ext_salesforce >= gt_salesforce * 0.8:
                        logger.info(f"  ✅ Salesforce participants match ({ext_salesforce}/{gt_salesforce})")
                        validation_results['passed'].append('salesforce_participants')
                    else:
                        logger.info(f"  ❌ Salesforce participants mismatch ({ext_salesforce}/{gt_salesforce})")
                        validation_results['failed'].append('salesforce_participants')
                        
            else:
                logger.info("  ❌ Could not find matching call")
                validation_results['failed'].append('call_not_found')
        
        # Validate transcript
        if ground_truth['call'].get('transcript'):
            logger.info("\n📝 Validating Transcript:")
            gt_transcript = ground_truth['call']['transcript']
            
            if matching_call and matching_call.get('transcript'):
                ext_segments = len(matching_call.get('transcript_segments', []))
                gt_segments = len(gt_transcript.get('segments', []))
                
                if ext_segments >= gt_segments * 0.8:
                    logger.info(f"  ✅ Transcript segments match ({ext_segments}/{gt_segments})")
                    validation_results['passed'].append('transcript_segments')
                else:
                    logger.info(f"  ❌ Transcript segments mismatch ({ext_segments}/{gt_segments})")
                    validation_results['failed'].append('transcript_segments')
            else:
                logger.info("  ⚠️ No transcript data to validate")
                validation_results['warnings'].append('no_transcript')
        
        # Calculate overall score
        total_checks = len(validation_results['passed']) + len(validation_results['failed'])
        if total_checks > 0:
            accuracy = (len(validation_results['passed']) / total_checks) * 100
            logger.info(f"\n📊 Validation Score: {accuracy:.1f}%")
            
            if accuracy >= 95:
                logger.info("✅ VALIDATION PASSED - Ready for production!")
            elif accuracy >= 80:
                logger.info("⚠️ VALIDATION WARNING - Some issues found")
            else:
                logger.info("❌ VALIDATION FAILED - Major issues detected")
        
        return validation_results
        
    async def run_full_validation(self):
        """Run the complete validation process"""
        logger.info("🚀 Starting Gong Full Validation")
        logger.info("=" * 50)
        
        # Step 1: Ensure fresh session
        if not await self.ensure_fresh_session():
            logger.error("❌ Failed to establish valid session")
            return False
        
        # Step 2: Load ground truth
        ground_truth = self.validator.load_ground_truth()
        
        # Step 3: Extract Gong data
        extracted_data = self.extract_gong_data()
        if not extracted_data:
            logger.error("❌ Failed to extract data from Gong")
            return False
        
        # Step 4: Compare and validate
        validation_results = self.compare_with_ground_truth(extracted_data, ground_truth)
        
        # Step 5: Save results
        results_file = Path(__file__).parent / "VALIDATION_RESULTS_FULL.json"
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'ground_truth_summary': {
                    'calls': 1,
                    'emails': len(ground_truth['emails']),
                    'transcript_segments': len(ground_truth['call'].get('transcript', {}).get('segments', []))
                },
                'extracted_summary': {
                    'calls': len(extracted_data.get('calls', [])),
                    'users': len(extracted_data.get('users', [])),
                    'conversations': len(extracted_data.get('conversations', []))
                },
                'validation_results': validation_results
            }, f, indent=2)
        
        logger.info(f"\n💾 Results saved to: {results_file}")
        
        return True

def main():
    """Main entry point"""
    validator = GongFullValidator()
    
    # Run async validation
    success = asyncio.run(validator.run_full_validation())
    
    if success:
        logger.info("\n🎉 Validation completed successfully!")
    else:
        logger.info("\n😞 Validation failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
