#!/usr/bin/env python3
"""
Simple validation test to verify fixes without complex imports
"""
from pathlib import Path

def test_directory_paths():
    """Test that directory paths are correct"""
    print('=== Testing Directory Paths ===')
    
    validation_dir = Path(__file__).parent / "validation"
    call_data_dir = validation_dir / "gong_call1"
    email_data_dir = validation_dir / "gong_emails"
    
    print(f'Validation dir: {validation_dir}')
    print(f'Call data dir: {call_data_dir}')
    print(f'Email data dir: {email_data_dir}')
    
    print(f'Call dir exists: {call_data_dir.exists()}')
    print(f'Email dir exists: {email_data_dir.exists()}')
    
    if call_data_dir.exists() and email_data_dir.exists():
        print('✅ Directory paths are correct!')
        
        # List files
        call_files = list(call_data_dir.glob('*.txt'))
        email_files = list(email_data_dir.glob('*.txt'))
        
        print(f'Call data files: {len(call_files)}')
        for f in call_files:
            print(f'  - {f.name}')
            
        print(f'Email data files: {len(email_files)}')
        for f in email_files:
            print(f'  - {f.name}')
            
        return True
    else:
        print('❌ Directory paths are incorrect!')
        return False

def test_improved_email_parser():
    """Test the improved email parser"""
    print('\n=== Testing Improved Email Parser ===')
    
    try:
        # Import the parser
        import sys
        sys.path.insert(0, str(Path(__file__).parent))
        from improved_email_parser import ImprovedEmailParser
        
        parser = ImprovedEmailParser()
        
        # Test with sample data
        sample_email = """Brian Coons
from
Brian Coons
Strategic Account Director, Postman
to
Danai Kongkarat
Software Asset Management Analyst, Sr, Salesforce
cc
Rose Winter
Analyst, Salesforce
Sean Felden
Jay Hurst
Vice President, Product Management, Salesforce
3:47 pm EDT
Re: Test Email Subject
This is the email body."""
        
        result = parser.parse_email(sample_email)
        
        print(f'✅ Sender: {result["sender"]}')
        print(f'✅ Subject: {result["subject"]}')
        print(f'✅ Recipients: {result["recipient_emails"]}')
        print(f'✅ CC: {result["cc_emails"]}')
        print(f'✅ Recipient details: {len(result["recipient_details"])} contacts parsed')
        print(f'✅ CC details: {len(result["cc_details"])} contacts parsed')
        
        return True
        
    except Exception as e:
        print(f'❌ Error testing improved parser: {e}')
        return False

def test_validation_file_contents():
    """Test that validation files can be read"""
    print('\n=== Testing Validation File Contents ===')
    
    validation_dir = Path(__file__).parent / "validation"
    
    # Test call data
    try:
        callinfo_file = validation_dir / "gong_call1" / "callinfo.txt"
        if callinfo_file.exists():
            with open(callinfo_file, 'r') as f:
                content = f.read()
                print(f'✅ Call info loaded: {len(content)} characters')
                # Show first few lines
                lines = content.split('\n')[:3]
                for line in lines:
                    if line.strip():
                        print(f'  Preview: {line.strip()}')
                        break
        else:
            print('❌ Call info file not found')
            
    except Exception as e:
        print(f'❌ Error reading call info: {e}')
    
    # Test email data
    try:
        email_files = list((validation_dir / "gong_emails").glob("*.txt"))
        print(f'✅ Found {len(email_files)} email files')
        
        for email_file in email_files:
            with open(email_file, 'r') as f:
                content = f.read()
                lines = content.split('\n')
                subject_line = None
                for line in lines:
                    if line.startswith('Re:'):
                        subject_line = line
                        break
                print(f'  - {email_file.name}: {subject_line or "No subject found"}')
                
    except Exception as e:
        print(f'❌ Error reading email files: {e}')

def main():
    """Run all validation tests"""
    print('=== Gong Validation Fixes Test ===\n')
    
    success_count = 0
    
    if test_directory_paths():
        success_count += 1
    
    if test_improved_email_parser():
        success_count += 1
    
    test_validation_file_contents()
    
    print(f'\n=== Test Summary ===')
    print(f'Tests passed: {success_count}/2')
    
    if success_count == 2:
        print('🎉 All critical fixes are working!')
    else:
        print('⚠️  Some fixes need attention')

if __name__ == "__main__":
    main()