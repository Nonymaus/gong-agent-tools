#!/usr/bin/env python3
"""
Gong Toolkit Integration Test

Tests the complete Gong toolkit functionality including authentication,
API client, and data extraction capabilities.
"""

import sys
import json
import time
from pathlib import Path

# Add the parent directory to the path to import the gong module
sys.path.append(str(Path(__file__).parent.parent))

from gong.agent import GongAgent
from gong.authentication.auth_manager import GongAuthenticationManager
from gong.api_client.client import GongAPIClient


def test_authentication():
    """Test authentication manager functionality."""
    print("🔐 Testing Authentication Manager...")
    
    # Use the authentication data file from our HAR capture
    auth_file = Path(__file__).parent.parent.parent.parent / "gong_authentication_analysis.json"
    
    if not auth_file.exists():
        print(f"❌ Authentication data file not found: {auth_file}")
        return False
    
    try:
        auth_manager = GongAuthenticationManager(str(auth_file))
        
        # Test authentication data loading
        summary = auth_manager.get_authentication_summary()
        print(f"   ✅ Loaded {summary['jwt_tokens_count']} JWT tokens")
        print(f"   ✅ Loaded {summary['session_tokens_count']} session tokens")
        print(f"   ✅ User: {summary['user_info']['email']}")
        print(f"   ✅ Base URL: {summary['base_url']}")
        print(f"   ✅ Security Score: {summary['security_score']}")
        
        # Test token validation
        for token_name, is_valid in summary['tokens_valid'].items():
            status = "✅ Valid" if is_valid else "⚠️ Expired"
            print(f"   {status} {token_name}")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        return False


def test_api_client():
    """Test API client functionality."""
    print("\n🌐 Testing API Client...")
    
    auth_file = Path(__file__).parent.parent.parent.parent / "gong_authentication_analysis.json"
    
    try:
        auth_manager = GongAuthenticationManager(str(auth_file))
        api_client = GongAPIClient(auth_manager)
        
        # Test connection
        connection_status = api_client.get_connection_status()
        
        print(f"   Base URL: {connection_status['base_url']}")
        print(f"   Workspace ID: {connection_status['workspace_id']}")
        print(f"   Connected: {'✅' if connection_status['connected'] else '❌'}")
        
        # Test individual endpoints
        for endpoint, result in connection_status['test_results'].items():
            status = "✅" if result else "❌"
            print(f"   {status} {endpoint}")
        
        return connection_status['connected']
        
    except Exception as e:
        print(f"❌ API client test failed: {e}")
        return False


def test_data_extraction():
    """Test data extraction functionality."""
    print("\n📊 Testing Data Extraction...")
    
    auth_file = Path(__file__).parent.parent.parent.parent / "gong_authentication_analysis.json"
    
    try:
        agent = GongAgent(str(auth_file))
        
        # Test connection first
        connection_test = agent.test_connection()
        if not connection_test['connected']:
            print("❌ Cannot test extraction - connection failed")
            return False
        
        print(f"   ✅ Connection test passed ({connection_test['test_duration']:.2f}s)")
        
        # Test individual extractions
        extraction_tests = [
            ('Users', agent.extract_users),
            ('Calls', lambda: agent.extract_calls(limit=10)),
            ('Deals', agent.extract_deals),
            ('Companies', agent.extract_companies),
            ('Contacts', agent.extract_contacts)
        ]
        
        results = {}
        total_time = 0
        
        for object_type, extraction_method in extraction_tests:
            print(f"   Testing {object_type} extraction...")
            
            start_time = time.time()
            result = extraction_method()
            extraction_time = time.time() - start_time
            total_time += extraction_time
            
            results[object_type.lower()] = result
            
            if result.success:
                print(f"   ✅ {object_type}: {result.count} objects ({extraction_time:.2f}s)")
            else:
                print(f"   ❌ {object_type}: Failed - {result.errors}")
        
        # Performance metrics
        metrics = agent.get_performance_metrics()
        print(f"\n📈 Performance Metrics:")
        print(f"   Total Time: {total_time:.2f}s")
        print(f"   Success Rate: {metrics['success_rate']:.1f}%")
        print(f"   Object Types: {metrics['object_types_extracted']}")
        print(f"   Total Objects: {metrics['total_objects']}")
        
        # Check performance targets
        meets_time = total_time < 30.0
        meets_success = metrics['success_rate'] > 95.0
        meets_objects = metrics['object_types_extracted'] >= 5
        
        print(f"\n🎯 Performance Targets:")
        print(f"   Time <30s: {'✅' if meets_time else '❌'} ({total_time:.2f}s)")
        print(f"   Success >95%: {'✅' if meets_success else '❌'} ({metrics['success_rate']:.1f}%)")
        print(f"   Objects ≥5: {'✅' if meets_objects else '❌'} ({metrics['object_types_extracted']})")
        
        return meets_time and meets_success and meets_objects
        
    except Exception as e:
        print(f"❌ Data extraction test failed: {e}")
        return False


def test_comprehensive_extraction():
    """Test comprehensive data extraction."""
    print("\n🚀 Testing Comprehensive Extraction...")
    
    auth_file = Path(__file__).parent.parent.parent.parent / "gong_authentication_analysis.json"
    
    try:
        agent = GongAgent(str(auth_file))
        
        # Run comprehensive extraction
        start_time = time.time()
        results = agent.extract_all_data()
        total_time = time.time() - start_time
        
        # Analyze results
        successful_types = sum(1 for r in results.values() if r.success)
        total_objects = sum(r.count for r in results.values())
        
        print(f"   ✅ Extracted {total_objects} objects from {successful_types}/{len(results)} types")
        print(f"   ✅ Total time: {total_time:.2f}s")
        
        # Detailed results
        for object_type, result in results.items():
            if result.success:
                print(f"   ✅ {object_type.capitalize()}: {result.count} objects ({result.extraction_time:.2f}s)")
            else:
                print(f"   ❌ {object_type.capitalize()}: Failed")
        
        # Final performance check
        meets_targets = (
            total_time < 30.0 and
            successful_types >= 5 and
            (successful_types / len(results)) > 0.95
        )
        
        return meets_targets
        
    except Exception as e:
        print(f"❌ Comprehensive extraction test failed: {e}")
        return False


def main():
    """Run all Gong toolkit tests."""
    print("🧪 GONG TOOLKIT INTEGRATION TEST")
    print("=" * 50)
    
    # Check if authentication data exists
    auth_file = Path(__file__).parent.parent.parent.parent / "gong_authentication_analysis.json"
    if not auth_file.exists():
        print(f"❌ Authentication data file not found: {auth_file}")
        print("   Please run HAR capture first to generate authentication data")
        return False
    
    # Run tests
    tests = [
        ("Authentication", test_authentication),
        ("API Client", test_api_client),
        ("Data Extraction", test_data_extraction),
        ("Comprehensive Extraction", test_comprehensive_extraction)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    print(f"\n{'='*50}")
    print("📋 TEST SUMMARY")
    print(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status} {test_name}")
    
    print(f"\n🎯 OVERALL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Gong toolkit is ready for production use.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
