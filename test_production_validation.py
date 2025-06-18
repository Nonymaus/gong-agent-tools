"""
Gong Production Validation Test

This test validates the Gong toolkit against real ground truth data with the requirement
of >95% field-level accuracy and 100% record completeness.

BLOCKING REQUIREMENT: This test MUST pass before considering Gong toolkit complete.

Requirements:
- >95% field-level accuracy against ground truth exports
- 100% record completeness (all export records found)
- Field-by-field comparison with specific mismatch reporting

Usage:
    # Run with fresh Gong session
    python test_production_validation.py
    
    # Or run with pytest
    pytest test_production_validation.py::test_production_validation_mandatory -v
"""

import logging
import pytest
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from test_real_data_validation import GongRealDataValidator
from agent import GongAgent, GongAgentError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.production
def test_production_validation_mandatory():
    """
    MANDATORY PRODUCTION TEST: Real data validation with >95% accuracy requirement
    
    This test MUST pass before considering Gong toolkit complete.
    
    Requirements:
    - >95% field-level accuracy against ground truth exports
    - 100% record completeness
    - Fresh Gong session required
    
    BLOCKING: This test blocks completion of Gong toolkit development
    """
    logger.info("🚨 MANDATORY PRODUCTION VALIDATION TEST STARTING")
    logger.info("📋 Requirements: >95% accuracy, 100% completeness")
    
    # Initialize validator
    validator = GongRealDataValidator()
    
    # Create Gong agent
    agent = GongAgent()
    
    # Look for fresh session files
    session_files = []
    
    # Look for HAR files in the _godcapture directory
    godcapture_dir = Path(__file__).parent.parent / "_godcapture" / "data"
    if godcapture_dir.exists():
        session_files.extend(godcapture_dir.glob("**/gong*.har"))
    
    # Look for local session files
    session_files.extend(Path(__file__).parent.glob("**/gong-*.har"))
    session_files.extend(Path(__file__).parent.glob("**/gong_session_*.json"))
    
    if not session_files:
        pytest.skip("❌ No Gong session file available - fresh session capture required for production validation")
    
    # Use the most recent session file
    latest_session = max(session_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"📁 Using session file: {latest_session}")
    
    try:
        agent.set_session(latest_session)
        
        # Test connection first
        connection_result = agent.test_connection()
        if not connection_result.get('connected', False):
            pytest.skip(f"❌ Gong session expired or invalid: {connection_result.get('error_message', 'Unknown error')}")
        
        logger.info("✅ Gong connection verified")
        
        # Run comprehensive validation
        logger.info("🔍 Running comprehensive validation against ground truth data...")
        validation_results = validator.run_comprehensive_validation(agent)
        
        # Log detailed results
        logger.info("=" * 60)
        logger.info("PRODUCTION VALIDATION RESULTS")
        logger.info("=" * 60)
        logger.info(f"Overall Success: {validation_results['overall_success']}")
        logger.info(f"Accuracy Met: {validation_results['accuracy_met']}")
        logger.info(f"Completeness Met: {validation_results['completeness_met']}")
        logger.info(f"Total Accuracy: {validation_results['summary']['total_accuracy']:.1%}")
        logger.info(f"Total Fields: {validation_results['summary']['total_fields']}")
        logger.info(f"Total Matched: {validation_results['summary']['total_matched']}")
        
        # Log call validation details
        if validation_results['call_validation']:
            call_val = validation_results['call_validation']
            logger.info(f"📞 Call Validation: {call_val.accuracy_percentage:.1%} accuracy")
            logger.info(f"📞 Call Fields: {call_val.matched_fields}/{call_val.total_fields}")
            
            if call_val.field_mismatches:
                logger.warning("📞 Call field mismatches:")
                for mismatch in call_val.field_mismatches:
                    logger.warning(f"  ❌ {mismatch.field_name}: {mismatch.error_message}")
            
            if call_val.missing_records:
                logger.error(f"📞 Missing call records: {call_val.missing_records}")
        
        # Log email validation details
        if validation_results['email_validation']:
            email_val = validation_results['email_validation']
            logger.info(f"📧 Email Validation: {email_val.accuracy_percentage:.1%} accuracy")
            logger.info(f"📧 Email Fields: {email_val.matched_fields}/{email_val.total_fields}")
            
            if email_val.field_mismatches:
                logger.warning("📧 Email field mismatches:")
                for mismatch in email_val.field_mismatches:
                    logger.warning(f"  ❌ {mismatch.field_name}: {mismatch.error_message}")
            
            if email_val.missing_records:
                logger.error(f"📧 Missing email records: {email_val.missing_records}")
        
        # Log any errors
        if validation_results['summary']['errors']:
            logger.error("🚨 Validation errors:")
            for error in validation_results['summary']['errors']:
                logger.error(f"  ❌ {error}")
        
        logger.info("=" * 60)
        
        # MANDATORY ASSERTIONS - THESE MUST PASS
        accuracy_threshold = validator.required_accuracy
        completeness_threshold = validator.required_completeness
        
        # Check accuracy requirement
        actual_accuracy = validation_results['summary']['total_accuracy']
        if actual_accuracy < accuracy_threshold:
            error_msg = (
                f"🚨 ACCURACY REQUIREMENT FAILED: {actual_accuracy:.1%} < {accuracy_threshold:.1%}\n"
                f"   Required: ≥{accuracy_threshold:.1%} field-level accuracy\n"
                f"   Actual: {actual_accuracy:.1%} accuracy\n"
                f"   Gap: {(accuracy_threshold - actual_accuracy):.1%} below threshold\n"
                f"   Fields matched: {validation_results['summary']['total_matched']}/{validation_results['summary']['total_fields']}"
            )
            logger.error(error_msg)
            pytest.fail(error_msg)
        
        # Check completeness requirement
        if not validation_results['completeness_met']:
            error_msg = (
                f"🚨 COMPLETENESS REQUIREMENT FAILED\n"
                f"   Required: {completeness_threshold:.0%} record completeness\n"
                f"   Issue: Missing or incomplete records detected"
            )
            logger.error(error_msg)
            pytest.fail(error_msg)
        
        # Check overall success
        if not validation_results['overall_success']:
            error_msg = (
                f"🚨 OVERALL VALIDATION FAILED\n"
                f"   Both accuracy and completeness requirements must be met\n"
                f"   Accuracy: {validation_results['accuracy_met']} (≥{accuracy_threshold:.1%})\n"
                f"   Completeness: {validation_results['completeness_met']} (≥{completeness_threshold:.0%})"
            )
            logger.error(error_msg)
            pytest.fail(error_msg)
        
        # SUCCESS!
        logger.info("🎉 PRODUCTION VALIDATION PASSED!")
        logger.info(f"✅ Accuracy: {actual_accuracy:.1%} (≥{accuracy_threshold:.1%} required)")
        logger.info(f"✅ Completeness: {completeness_threshold:.0%} (≥{completeness_threshold:.0%} required)")
        logger.info("✅ All requirements met - Gong toolkit ready for production!")
        
    except GongAgentError as e:
        if "session may be expired" in str(e).lower() or "invalid token" in str(e).lower():
            pytest.skip(f"❌ Gong session expired: {e}")
        else:
            logger.error(f"🚨 Gong agent error: {e}")
            raise
    except Exception as e:
        logger.error(f"🚨 Unexpected error during validation: {e}")
        raise


def test_validation_framework_ready():
    """Test that validation framework is ready for production use"""
    logger.info("🔧 Testing validation framework readiness")
    
    validator = GongRealDataValidator()
    
    # Test ground truth data loading
    call_data = validator.load_ground_truth_call_data()
    email_data = validator.load_ground_truth_email_data()
    
    assert call_data is not None
    assert email_data is not None
    assert len(email_data) >= 2
    
    # Test validation directory structure
    assert validator.validation_dir.exists()
    assert validator.call_data_dir.exists()
    assert validator.email_data_dir.exists()
    
    # Test requirements are set correctly
    assert validator.required_accuracy == 0.95
    assert validator.required_completeness == 1.0
    
    logger.info("✅ Validation framework is ready for production testing")


if __name__ == "__main__":
    # Run production validation directly
    logger.info("🚀 Running Gong Production Validation")
    
    try:
        test_production_validation_mandatory()
        print("\n🎉 PRODUCTION VALIDATION PASSED!")
        print("✅ Gong toolkit meets all requirements and is ready for production use")
    except Exception as e:
        print(f"\n❌ PRODUCTION VALIDATION FAILED: {e}")
        print("🔧 Fresh Gong session capture required for validation")
        sys.exit(1)
