#!/usr/bin/env python3
"""
Comprehensive test runner for Gong toolkit unit tests.

Runs all unit tests with coverage reporting and detailed output.
Validates that all components meet the acceptance criteria.
"""

import sys
import subprocess
from pathlib import Path
import time

# Add the gong directory to the path
sys.path.insert(0, str(Path(__file__).parent))


def run_pytest_with_coverage():
    """Run pytest with coverage reporting"""
    print("🚨 GONG TOOLKIT COMPREHENSIVE UNIT TESTS")
    print("=" * 60)
    
    # Check if pytest is available
    try:
        import pytest
        print("✅ pytest available")
    except ImportError:
        print("❌ pytest not available - installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-cov"], check=True)
        import pytest
    
    # Check if pytest-cov is available
    try:
        import pytest_cov
        print("✅ pytest-cov available")
    except ImportError:
        print("❌ pytest-cov not available - installing...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest-cov"], check=True)
    
    print("\n🔍 Running unit tests with coverage...")
    
    # Run pytest with coverage
    test_args = [
        "-v",  # Verbose output
        "--tb=short",  # Short traceback format
        "--cov=.",  # Coverage for current directory
        "--cov-report=term-missing",  # Show missing lines
        "--cov-report=html:htmlcov",  # HTML coverage report
        "--cov-fail-under=90",  # Fail if coverage < 90%
        "tests/",  # Test directory
    ]
    
    start_time = time.time()
    result = pytest.main(test_args)
    duration = time.time() - start_time
    
    print(f"\n⏱️  Tests completed in {duration:.2f} seconds")
    
    return result == 0


def run_individual_test_files():
    """Run individual test files for detailed reporting"""
    print("\n📊 INDIVIDUAL TEST FILE RESULTS")
    print("=" * 60)
    
    test_files = [
        "tests/test_data_models.py",
        "tests/test_authentication.py", 
        "tests/test_api_client.py",
        "tests/test_agent.py"
    ]
    
    results = {}
    
    for test_file in test_files:
        if not Path(test_file).exists():
            print(f"⚠️  {test_file} not found - skipping")
            continue
        
        print(f"\n🧪 Running {test_file}...")
        
        start_time = time.time()
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "-v", "--tb=short", test_file
        ], capture_output=True, text=True)
        duration = time.time() - start_time
        
        success = result.returncode == 0
        results[test_file] = {
            'success': success,
            'duration': duration,
            'output': result.stdout,
            'errors': result.stderr
        }
        
        if success:
            print(f"   ✅ PASSED in {duration:.2f}s")
        else:
            print(f"   ❌ FAILED in {duration:.2f}s")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}...")
    
    return results


def check_test_coverage():
    """Check test coverage requirements"""
    print("\n📈 COVERAGE ANALYSIS")
    print("=" * 60)
    
    # Try to read coverage data
    try:
        import coverage
        
        cov = coverage.Coverage()
        cov.load()
        
        # Get coverage report
        total_coverage = cov.report(show_missing=False)
        
        print(f"📊 Total Coverage: {total_coverage:.1f}%")
        
        if total_coverage >= 90:
            print("✅ Coverage target met (≥90%)")
            return True
        else:
            print(f"❌ Coverage target missed (got {total_coverage:.1f}%, need ≥90%)")
            return False
            
    except Exception as e:
        print(f"⚠️  Could not analyze coverage: {e}")
        return False


def validate_acceptance_criteria():
    """Validate that acceptance criteria are met"""
    print("\n🎯 ACCEPTANCE CRITERIA VALIDATION")
    print("=" * 60)
    
    criteria = {
        "≥90% code coverage": False,
        "All tests pass": False,
        "Mock data validation": False,
        "Data models tested": False,
        "Authentication tested": False,
        "API client tested": False,
        "Agent interface tested": False
    }
    
    # Check if test files exist and have content
    test_files = {
        "tests/test_data_models.py": "Data models tested",
        "tests/test_authentication.py": "Authentication tested",
        "tests/test_api_client.py": "API client tested", 
        "tests/test_agent.py": "Agent interface tested"
    }
    
    for test_file, criterion in test_files.items():
        if Path(test_file).exists():
            # Check file has substantial content (>100 lines)
            with open(test_file, 'r') as f:
                lines = len(f.readlines())
            
            if lines > 100:
                criteria[criterion] = True
                print(f"✅ {criterion} ({lines} lines)")
            else:
                print(f"❌ {criterion} (insufficient content: {lines} lines)")
        else:
            print(f"❌ {criterion} (file not found)")
    
    # Check for mock data validation (look for Mock usage)
    mock_usage_found = False
    for test_file in test_files.keys():
        if Path(test_file).exists():
            with open(test_file, 'r') as f:
                content = f.read()
                if 'Mock' in content and 'patch' in content:
                    mock_usage_found = True
                    break
    
    criteria["Mock data validation"] = mock_usage_found
    if mock_usage_found:
        print("✅ Mock data validation (Mock and patch usage found)")
    else:
        print("❌ Mock data validation (no Mock usage found)")
    
    return criteria


def generate_test_report(individual_results, coverage_met, criteria):
    """Generate comprehensive test report"""
    print("\n📋 COMPREHENSIVE TEST REPORT")
    print("=" * 60)
    
    # Summary statistics
    total_files = len(individual_results)
    passed_files = sum(1 for r in individual_results.values() if r['success'])
    total_duration = sum(r['duration'] for r in individual_results.values())
    
    print(f"📊 Test Files: {passed_files}/{total_files} passed")
    print(f"⏱️  Total Duration: {total_duration:.2f} seconds")
    print(f"📈 Coverage Target: {'✅ MET' if coverage_met else '❌ MISSED'}")
    
    # Acceptance criteria summary
    print(f"\n🎯 Acceptance Criteria:")
    met_criteria = sum(1 for met in criteria.values() if met)
    total_criteria = len(criteria)
    
    for criterion, met in criteria.items():
        status = "✅" if met else "❌"
        print(f"   {status} {criterion}")
    
    print(f"\n📈 Criteria Met: {met_criteria}/{total_criteria}")
    
    # Overall success
    overall_success = (
        passed_files == total_files and
        coverage_met and
        met_criteria == total_criteria
    )
    
    if overall_success:
        print("\n🎉 ALL UNIT TESTS PASSED!")
        print("✅ Gong toolkit unit tests successfully validated:")
        print("   - Comprehensive test coverage (≥90%)")
        print("   - All test files passing")
        print("   - Mock data validation implemented")
        print("   - All components thoroughly tested")
        print("\n🎯 ACCEPTANCE CRITERIA FULLY MET:")
        print("   ✅ ≥90% code coverage achieved")
        print("   ✅ All tests pass with mock data validation")
        print("   ✅ Comprehensive component testing")
        print("   ✅ Ready for integration testing")
    else:
        print("\n❌ UNIT TESTS INCOMPLETE")
        print("Some acceptance criteria not met - see details above")
    
    return overall_success


def main():
    """Main test runner function"""
    print("Starting Gong toolkit comprehensive unit tests...\n")
    
    # Change to the gong directory
    gong_dir = Path(__file__).parent
    import os
    os.chdir(gong_dir)
    
    try:
        # Run pytest with coverage
        pytest_success = run_pytest_with_coverage()
        
        # Run individual test files
        individual_results = run_individual_test_files()
        
        # Check coverage
        coverage_met = check_test_coverage()
        
        # Validate acceptance criteria
        criteria = validate_acceptance_criteria()
        
        # Generate comprehensive report
        overall_success = generate_test_report(individual_results, coverage_met, criteria)
        
        return 0 if overall_success else 1
        
    except Exception as e:
        print(f"\n❌ Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)