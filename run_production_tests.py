#!/usr/bin/env python3
"""
Production functionality test runner for Gong toolkit.

Runs comprehensive production validation tests including:
- Real Gong environment authentication
- Production API functionality validation
- Data extraction performance testing
- Production data quality validation
- Success metrics verification
"""

import sys
import time
import json
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'gong_production_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


def check_prerequisites():
    """Check that all prerequisites for production testing are met."""
    logger.info("🔍 Checking Production Test Prerequisites")
    
    prerequisites = {
        'har_analysis_file': False,
        'gong_toolkit_modules': False,
        'test_environment': False
    }
    
    # Check for HAR analysis file
    analysis_file = Path(__file__).parent.parent / "_godcapture/data/gong-multitab-capture/analysis/godcapture_analysis.json"
    if analysis_file.exists():
        try:
            with open(analysis_file, 'r') as f:
                analysis_data = json.load(f)
            
            if analysis_data.get('artifacts'):
                prerequisites['har_analysis_file'] = True
                logger.info("  ✓ HAR analysis file found with artifacts")
            else:
                logger.warning("  ⚠️  HAR analysis file exists but has no artifacts")
        except Exception as e:
            logger.warning(f"  ⚠️  HAR analysis file invalid: {e}")
    else:
        logger.warning("  ❌ HAR analysis file not found")
        logger.info("    Run: cd app_backend/agent_tools/_godcapture && python _godcapture.py")
    
    # Check for Gong toolkit modules
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from authentication import GongAuthenticationManager
        from api_client import GongAPIClient
        from agent import GongAgent
        prerequisites['gong_toolkit_modules'] = True
        logger.info("  ✓ Gong toolkit modules importable")
    except ImportError as e:
        logger.error(f"  ❌ Gong toolkit modules not importable: {e}")
    
    # Check test environment
    try:
        import pytest
        prerequisites['test_environment'] = True
        logger.info("  ✓ Test environment ready")
    except ImportError:
        logger.error("  ❌ pytest not available")
    
    # Summary
    ready_count = sum(prerequisites.values())
    total_count = len(prerequisites)
    
    logger.info(f"\n📊 Prerequisites Status: {ready_count}/{total_count} ready")
    
    if ready_count == total_count:
        logger.info("✅ All prerequisites met - ready for production testing")
        return True
    else:
        logger.warning("⚠️  Some prerequisites not met - tests may fail")
        return False


def run_production_authentication_test():
    """Run production authentication functionality test."""
    logger.info("\n🔐 Running Production Authentication Test")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from authentication import GongAuthenticationManager
        
        # Load analysis data
        analysis_file = Path(__file__).parent.parent / "_godcapture/data/gong-multitab-capture/analysis/godcapture_analysis.json"
        
        if not analysis_file.exists():
            logger.error("❌ Analysis file not found")
            return False
        
        with open(analysis_file, 'r') as f:
            analysis_data = json.load(f)
        
        # Test authentication
        auth_manager = GongAuthenticationManager()
        session = auth_manager.extract_session_from_analysis_data(analysis_data)
        
        if session:
            logger.info(f"✅ Authentication test passed:")
            logger.info(f"  User: {session.user_email}")
            logger.info(f"  Cell: {session.cell_id}")
            logger.info(f"  Tokens: {len(session.authentication_tokens)}")
            return True
        else:
            logger.error("❌ Authentication test failed: No session extracted")
            return False
            
    except Exception as e:
        logger.error(f"❌ Authentication test failed: {e}")
        return False


def run_production_api_test():
    """Run production API functionality test."""
    logger.info("\n🌐 Running Production API Test")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from authentication import GongAuthenticationManager
        from api_client import GongAPIClient
        
        # Load analysis data
        analysis_file = Path(__file__).parent.parent / "_godcapture/data/gong-multitab-capture/analysis/godcapture_analysis.json"
        
        with open(analysis_file, 'r') as f:
            analysis_data = json.load(f)
        
        # Setup API client
        auth_manager = GongAuthenticationManager()
        session = auth_manager.extract_session_from_analysis_data(analysis_data)
        
        api_client = GongAPIClient()
        api_client.set_session(session)
        
        # Test connection
        connection_status = api_client.get_connection_status()
        
        if connection_status.get('connected'):
            logger.info(f"✅ API test passed:")
            logger.info(f"  Base URL: {connection_status.get('base_url')}")
            logger.info(f"  Workspace: {connection_status.get('workspace_id')}")
            return True
        else:
            logger.error("❌ API test failed: Connection not established")
            return False
            
    except Exception as e:
        logger.error(f"❌ API test failed: {e}")
        return False


def run_production_extraction_test():
    """Run production data extraction test."""
    logger.info("\n📊 Running Production Data Extraction Test")
    
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from agent import GongAgent
        
        # Load analysis data
        analysis_file = Path(__file__).parent.parent / "_godcapture/data/gong-multitab-capture/analysis/godcapture_analysis.json"
        
        # Test agent
        agent = GongAgent(str(analysis_file))
        
        # Test connection
        connection_test = agent.test_connection()
        
        if not connection_test.get('connected'):
            logger.error("❌ Extraction test failed: Agent connection failed")
            return False
        
        # Test sample extractions
        extraction_results = {}
        
        try:
            calls = agent.extract_calls(limit=5)
            extraction_results['calls'] = len(calls) if calls else 0
            logger.info(f"  Calls extracted: {extraction_results['calls']}")
        except Exception as e:
            logger.warning(f"  Calls extraction failed: {e}")
            extraction_results['calls'] = 0
        
        try:
            users = agent.extract_users()
            extraction_results['users'] = len(users) if users else 0
            logger.info(f"  Users extracted: {extraction_results['users']}")
        except Exception as e:
            logger.warning(f"  Users extraction failed: {e}")
            extraction_results['users'] = 0
        
        # Calculate success
        total_extracted = sum(extraction_results.values())
        successful_types = sum(1 for count in extraction_results.values() if count > 0)
        
        if successful_types >= 1 and total_extracted >= 3:
            logger.info(f"✅ Extraction test passed:")
            logger.info(f"  Object types: {successful_types}")
            logger.info(f"  Total records: {total_extracted}")
            return True
        else:
            logger.error(f"❌ Extraction test failed: Insufficient data extracted")
            return False
            
    except Exception as e:
        logger.error(f"❌ Extraction test failed: {e}")
        return False


def run_full_production_test_suite():
    """Run the complete production test suite using pytest."""
    logger.info("\n🧪 Running Full Production Test Suite")
    
    try:
        import pytest
        
        # Run production tests
        test_file = Path(__file__).parent / "tests/test_production_functionality.py"
        
        if not test_file.exists():
            logger.error("❌ Production test file not found")
            return False
        
        # Run pytest with production marker
        exit_code = pytest.main([
            str(test_file),
            "-v",
            "--tb=short",
            "-m", "production",
            "--capture=no"
        ])
        
        if exit_code == 0:
            logger.info("✅ Full production test suite passed")
            return True
        else:
            logger.error(f"❌ Full production test suite failed (exit code: {exit_code})")
            return False
            
    except Exception as e:
        logger.error(f"❌ Full production test suite failed: {e}")
        return False


def main():
    """Main test runner function."""
    logger.info("🚀 Starting Gong Toolkit Production Functionality Tests")
    logger.info("=" * 80)
    
    start_time = time.time()
    
    # Check prerequisites
    prerequisites_ok = check_prerequisites()
    
    if not prerequisites_ok:
        logger.error("❌ Prerequisites not met - aborting tests")
        return 1
    
    # Run individual tests
    test_results = {
        'authentication': run_production_authentication_test(),
        'api': run_production_api_test(),
        'extraction': run_production_extraction_test(),
        'full_suite': run_full_production_test_suite()
    }
    
    # Summary
    total_time = time.time() - start_time
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    logger.info("\n" + "=" * 80)
    logger.info("📊 Production Test Results Summary")
    logger.info("=" * 80)
    
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"  {test_name.title()}: {status}")
    
    logger.info(f"\nOverall Results:")
    logger.info(f"  Tests passed: {passed_tests}/{total_tests}")
    logger.info(f"  Success rate: {(passed_tests/total_tests)*100:.1f}%")
    logger.info(f"  Total time: {total_time:.2f}s")
    
    if passed_tests == total_tests:
        logger.info("\n🎉 All production functionality tests passed!")
        logger.info("✅ Gong toolkit is ready for production use")
        return 0
    else:
        logger.warning(f"\n⚠️  {total_tests - passed_tests} test(s) failed")
        logger.info("🔧 Review failed tests and fix issues before production deployment")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
