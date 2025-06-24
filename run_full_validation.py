"""
Module: run_full_validation
Type: Entrypoint

Purpose:
Gong integration component handling specific functionality within the CS-Ascension platform.

Data Flow:
- Input: Configuration parameters, Authentication credentials
- Processing: Input validation, Data extraction, API interaction
- Output: Dictionary responses, Error states and exceptions

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: asyncio, logging, validation_test_standalone, playwright.async_api, agent, traceback, traceback, traceback, traceback
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
#!/usr/bin/env python3

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

# Import validation module
from validation_test_standalone import GongRealDataValidator


async def capture_authentication():
    """Capture fresh Gong authentication"""
    logger.info("🔐 Capturing fresh Gong authentication...")
    
    try:
        # Import here to avoid circular imports
        from playwright.async_api import async_playwright
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=site-per-process',
                    '--disable-dev-shm-usage'
                ]
            )
            
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            # Enable HAR recording
            await context.route_from_har(
                Path(__file__).parent / "gong_session.har",
                update=True,
                update_mode='full'
            )
            
            page = await context.new_page()
            
            logger.info("🌐 Navigating to Gong...")
            await page.goto('https://app.gong.io')
            
            logger.info("⏳ Waiting for authentication... Please complete login in the browser")
            logger.info("📌 The script will continue once you reach the Gong dashboard")
            
            # Wait for successful login - look for Gong dashboard elements
            try:
                await page.wait_for_selector('[data-testid="navbar-logo"]', timeout=300000)  # 5 minute timeout
                logger.info("✅ Authentication successful!")
                
                # Save HAR file
                await context.close()
                await browser.close()
                
                logger.info("💾 HAR file saved")
                return True
                
            except Exception as e:
                logger.error(f"❌ Authentication timeout: {e}")
                await browser.close()
                return False
                
    except Exception as e:
        logger.error(f"❌ Failed to capture authentication: {e}")
        import traceback
        traceback.print_exc()
        return False


def extract_data_with_agent():
    """Extract data using Gong agent with captured authentication"""
    logger.info("📊 Extracting data with Gong agent...")
    
    try:
        from agent import GongAgent
        
        # Initialize agent
        agent = GongAgent()
        
        # Test connection
        connection_result = agent.test_connection()
        if not connection_result.get('connected', False):
            logger.error(f"❌ Failed to connect: {connection_result.get('error_message', 'Unknown error')}")
            return None
        
        logger.info("✅ Connected to Gong successfully")
        
        # Extract all data
        logger.info("🔄 Extracting data from Gong...")
        extracted_data = agent.extract_all_data()
        
        # Log summary
        if extracted_data and 'data' in extracted_data:
            data = extracted_data['data']
            logger.info(f"📞 Extracted {len(data.get('calls', []))} calls")
            logger.info(f"📧 Extracted {len(data.get('conversations', []))} conversations")
            logger.info(f"👥 Extracted {len(data.get('users', []))} users")
        
        return extracted_data
        
    except Exception as e:
        logger.error(f"❌ Failed to extract data: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_validation(extracted_data: Dict[str, Any]):
    """Run validation against ground truth data"""
    logger.info("🔍 Running validation against ground truth...")
    
    try:
        # Create validator
        validator = GongRealDataValidator()
        
        # Run validation
        validation_results = validator.validate_against_ground_truth(extracted_data)
        
        # Print results
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION RESULTS")
        logger.info("=" * 60)
        
        logger.info(f"Overall Success: {'✅ PASS' if validation_results['overall_success'] else '❌ FAIL'}")
        logger.info(f"Accuracy: {validation_results['summary']['total_accuracy']:.1%} (Required: {validator.required_accuracy:.1%})")
        logger.info(f"Fields Validated: {validation_results['summary']['total_fields']}")
        logger.info(f"Fields Matched: {validation_results['summary']['total_matched']}")
        
        # Save results
        results_file = Path(__file__).parent / f"validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(validation_results, f, indent=2)
        logger.info(f"📄 Results saved to: {results_file}")
        
        return validation_results
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Main function"""
    logger.info("🚀 Starting Gong Full Validation Test")
    logger.info("=" * 60)
    
    # Step 1: Capture authentication
    auth_success = await capture_authentication()
    if not auth_success:
        logger.error("❌ Authentication capture failed")
        return 1
    
    # Step 2: Extract data
    extracted_data = extract_data_with_agent()
    if not extracted_data:
        logger.error("❌ Data extraction failed")
        return 1
    
    # Save extracted data for debugging
    extracted_file = Path(__file__).parent / f"extracted_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(extracted_file, 'w') as f:
        json.dump(extracted_data, f, indent=2)
    logger.info(f"📄 Extracted data saved to: {extracted_file}")
    
    # Step 3: Run validation
    validation_results = run_validation(extracted_data)
    if not validation_results:
        logger.error("❌ Validation execution failed")
        return 1
    
    # Return success/failure based on validation results
    if validation_results['overall_success']:
        logger.info("\n✅ VALIDATION PASSED - All requirements met!")
        return 0
    else:
        logger.error("\n❌ VALIDATION FAILED - Requirements not met!")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\n⚠️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)