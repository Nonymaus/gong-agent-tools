"""
Module: test_gong_navigation_regression
Type: Test

Purpose:
Unit tests for Gong functionality ensuring reliability and correctness.

Data Flow:
- Input: Configuration parameters, Authentication credentials
- Processing: Input validation, Data extraction
- Output: Dictionary responses, Error states and exceptions

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: asyncio, logging, authentication.session_extractor
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
import asyncio
import logging
import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GongNavigationRegressionTest:
    """Fast regression test for Gong navigation functionality."""
    
    def __init__(self):
        self.max_test_time = 25  # Maximum test duration in seconds (optimized for minimal data collection)
        self.min_auth_tokens = 1  # Minimum authentication tokens required
        self.required_url_pattern = 'gong.io'  # Required URL pattern for success
        
    async def run_regression_test(self):
        """
        Run the complete regression test with strict timing and success criteria.
        
        Returns:
            tuple: (success: bool, elapsed_time: float, result_data: dict)
        """
        start_time = time.time()
        
        try:
            logger.info("🧪 Starting Gong Navigation Regression Test")
            logger.info(f"⏱️ Maximum test time: {self.max_test_time} seconds")
            logger.info(f"🎯 Success criteria: URL contains '{self.required_url_pattern}', ≥{self.min_auth_tokens} auth tokens")
            
            # Import here to avoid import delays during test discovery
            from authentication.session_extractor import GongSessionExtractor
            
            # Initialize extractor with optimized settings for testing
            extractor = GongSessionExtractor(
                headless=True,  # Headless for CI/CD speed
                session_timeout=self.max_test_time,
                minimal_mode=True,  # Disable heavy data collection
                collect_js_variables=False,  # Skip slow JS extraction
                collect_response_bodies=False,  # Skip large response analysis
                early_exit_on_navigation=True  # Exit immediately on success
            )
            
            # Run navigation with strict timeout
            logger.info("🚀 Starting navigation test...")
            result = await asyncio.wait_for(
                extractor.capture_fresh_session(target_app="Gong"),
                timeout=self.max_test_time
            )
            
            elapsed_time = time.time() - start_time
            
            # Validate success criteria
            success, validation_details = self._validate_success_criteria(result, elapsed_time)
            
            # Log results
            self._log_test_results(success, elapsed_time, result, validation_details)
            
            return success, elapsed_time, result
            
        except asyncio.TimeoutError:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ Test timed out after {elapsed_time:.1f} seconds")
            return False, elapsed_time, None
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"❌ Test failed with exception: {e}")
            return False, elapsed_time, None
    
    def _validate_success_criteria(self, result, elapsed_time):
        """
        Validate the test result against success criteria.
        
        Args:
            result: Session capture result
            elapsed_time: Test execution time
            
        Returns:
            tuple: (success: bool, validation_details: dict)
        """
        validation_details = {
            'result_not_none': result is not None,
            'within_time_limit': elapsed_time < self.max_test_time,
            'has_gong_url': False,
            'has_auth_tokens': False,
            'auth_token_count': 0,
            'current_url': 'unknown'
        }
        
        if result:
            # Check URL pattern
            current_url = result.get('current_url', '')
            validation_details['current_url'] = current_url
            validation_details['has_gong_url'] = self.required_url_pattern in current_url.lower()
            
            # Check authentication tokens
            auth_tokens = result.get('authentication_tokens', [])
            validation_details['auth_token_count'] = len(auth_tokens)
            validation_details['has_auth_tokens'] = len(auth_tokens) >= self.min_auth_tokens
        
        # Overall success
        success = all([
            validation_details['result_not_none'],
            validation_details['within_time_limit'],
            validation_details['has_gong_url'],
            validation_details['has_auth_tokens']
        ])
        
        return success, validation_details
    
    def _log_test_results(self, success, elapsed_time, result, validation_details):
        """Log detailed test results."""
        logger.info("=" * 60)
        logger.info("GONG NAVIGATION REGRESSION TEST RESULTS")
        logger.info("=" * 60)
        
        # Overall result
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"Overall Result: {status}")
        logger.info(f"Execution Time: {elapsed_time:.2f} seconds")
        
        # Detailed validation
        logger.info("\nValidation Details:")
        logger.info(f"  📊 Result returned: {'✅' if validation_details['result_not_none'] else '❌'}")
        logger.info(f"  ⏱️ Within time limit ({self.max_test_time}s): {'✅' if validation_details['within_time_limit'] else '❌'}")
        logger.info(f"  🌐 Contains '{self.required_url_pattern}': {'✅' if validation_details['has_gong_url'] else '❌'}")
        logger.info(f"  🔑 Auth tokens (≥{self.min_auth_tokens}): {'✅' if validation_details['has_auth_tokens'] else '❌'}")
        
        # Additional details
        if result:
            logger.info(f"\nSession Details:")
            logger.info(f"  🌐 Current URL: {validation_details['current_url']}")
            logger.info(f"  🔑 Auth tokens found: {validation_details['auth_token_count']}")
            logger.info(f"  👤 User: {result.get('user_email', 'unknown')}")
            logger.info(f"  🏢 Platform: {result.get('platform', 'unknown')}")
            logger.info(f"  📡 Endpoints discovered: {result.get('endpoints_discovered', 0)}")
        
        logger.info("=" * 60)


async def main():
    """Main test function."""
    test = GongNavigationRegressionTest()
    
    try:
        success, elapsed_time, result = await test.run_regression_test()
        
        # Exit with appropriate code for CI/CD
        exit_code = 0 if success else 1
        
        if success:
            logger.info("🎉 Regression test PASSED - Navigation is working correctly!")
        else:
            logger.error("💥 Regression test FAILED - Navigation needs attention!")
        
        return exit_code
        
    except Exception as e:
        logger.error(f"💥 Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
