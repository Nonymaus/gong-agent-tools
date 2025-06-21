#!/usr/bin/env python3
"""
Quick test script to verify all fixes are working
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Import the validator from the prefixed file
import importlib.util

# Load the validation module
spec = importlib.util.spec_from_file_location(
    "test_real_data_validation", 
    "????test_real_data_validation.py"
)
validation_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation_module)

GongRealDataValidator = validation_module.GongRealDataValidator

def test_validation_fixes():
    """Test that all validation fixes are working"""
    print('=== Testing Gong Validation Fixes ===\n')
    
    validator = GongRealDataValidator()
    
    # Test 1: Directory paths are correct
    print('1. Testing directory paths...')
    print(f'   Call data dir: {validator.call_data_dir}')
    print(f'   Email data dir: {validator.email_data_dir}')
    print(f'   Call dir exists: {validator.call_data_dir.exists()}')
    print(f'   Email dir exists: {validator.email_data_dir.exists()}')
    
    if validator.call_data_dir.exists() and validator.email_data_dir.exists():
        print('   ✅ Directory paths are correct\n')
    else:
        print('   ❌ Directory paths still incorrect\n')
    
    # Test 2: Load ground truth data
    print('2. Testing ground truth data loading...')
    try:
        call_data = validator.load_ground_truth_call_data()
        print(f'   ✅ Call data loaded: {len(call_data)} sections')
        for key in call_data.keys():
            print(f'     - {key}')
    except Exception as e:
        print(f'   ❌ Error loading call data: {e}')
    
    try:
        email_data = validator.load_ground_truth_email_data()
        print(f'   ✅ Email data loaded: {len(email_data)} emails')
        for email in email_data:
            subject = email.get('subject', 'No subject')
            sender = email.get('sender', 'No sender')
            print(f'     - "{subject}" from {sender}')
    except Exception as e:
        print(f'   ❌ Error loading email data: {e}')
    
    print('\n3. Testing improved email parser...')
    try:
        from improved_email_parser import ImprovedEmailParser
        parser = ImprovedEmailParser()
        
        # Test with email1.txt
        with open('validation/gong_emails/email1.txt', 'r') as f:
            content = f.read()
        
        result = parser.parse_email(content)
        print(f'   ✅ Sender: {result["sender"]}')
        print(f'   ✅ Subject: {result["subject"]}')
        print(f'   ✅ Recipients: {result["recipient_emails"]}')
        print(f'   ✅ Recipient details: {len(result["recipient_details"])} contacts')
        
    except Exception as e:
        print(f'   ❌ Error testing improved parser: {e}')
    
    print('\n=== Validation Fix Test Complete ===')

if __name__ == "__main__":
    test_validation_fixes()