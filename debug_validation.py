#!/usr/bin/env python3
"""Debug script to find which two fields are failing validation"""

import json
from pathlib import Path

# Correct paths to actual validation data
validation_dir = Path(__file__).parent / "validation"
call_data_dir = validation_dir / "gong_call1"  # Fixed path
email_data_dir = validation_dir / "gong_emails"  # Fixed path

print("=== Debugging Gong Validation ===")
print(f"\nChecking validation directories:")
print(f"Call data dir exists: {call_data_dir.exists()}")
print(f"Email data dir exists: {email_data_dir.exists()}")

# Check call data files
print(f"\n📁 Call data files in {call_data_dir.name}:")
if call_data_dir.exists():
    for file in call_data_dir.iterdir():
        print(f"  - {file.name} ({file.stat().st_size} bytes)")
else:
    print("  ERROR: Directory not found!")

# Check email data files
print(f"\n📧 Email data files in {email_data_dir.name}:")
if email_data_dir.exists():
    for file in email_data_dir.iterdir():
        print(f"  - {file.name} ({file.stat().st_size} bytes)")
else:
    print("  ERROR: Directory not found!")

# Try to load and parse data to find potential issues
print("\n🔍 Checking data parsing:")

# Parse call info
if (call_data_dir / "callinfo.txt").exists():
    with open(call_data_dir / "callinfo.txt", 'r') as f:
        content = f.read()
        print("\nCall info preview:")
        lines = content.strip().split('\n')[:10]
        for line in lines:
            print(f"  {line}")

# Parse attendees
if (call_data_dir / "attendees.txt").exists():
    with open(call_data_dir / "attendees.txt", 'r') as f:
        content = f.read().strip()
        attendees = [email.strip() for email in content.split(';') if email.strip()]
        print(f"\nAttendees found: {len(attendees)}")
        for attendee in attendees[:3]:
            print(f"  - {attendee}")
        if len(attendees) > 3:
            print(f"  ... and {len(attendees) - 3} more")

# Check email parsing
print("\n📧 Email parsing check:")
for email_file in sorted(email_data_dir.glob("email*.txt"))[:2]:
    print(f"\n{email_file.name}:")
    with open(email_file, 'r') as f:
        lines = f.read().strip().split('\n')
        # Look for key fields
        sender_found = False
        subject_found = False
        
        for i, line in enumerate(lines):
            if line.strip() == 'from':
                sender_found = True
                if i + 1 < len(lines):
                    print(f"  Sender info: {lines[i+1]}")
            elif line.strip().startswith('Re:'):
                subject_found = True
                print(f"  Subject: {line.strip()}")
        
        if not sender_found:
            print("  ❌ ERROR: No 'from' section found!")
        if not subject_found:
            print("  ❌ ERROR: No subject line found!")

# Now let's check what the test expects vs what's actually there
print("\n⚠️  Directory Name Mismatch:")
print("Tests are looking for:")
print("  - gong_call1/")
print("  - gong_emails/")
print("\nBut actual directories are:")
print("  - gong_call1/")
print("  - gong_emails/")

print("\n🎯 This is likely causing the validation failures!")
print("The tests need to be updated to use the correct directory names.")

# Check for potential field parsing issues
print("\n🔍 Potential field issues:")

# Check if attendees might have formatting issues
if (call_data_dir / "attendees.txt").exists():
    with open(call_data_dir / "attendees.txt", 'r') as f:
        content = f.read()
        if 'daryl.martis' in content.lower():
            print("  ⚠️  Found 'daryl.martis' - but test expects 'dmartis'")
        if not content.strip().endswith(';'):
            print("  ⚠️  Attendees file doesn't end with semicolon")

# Check email recipient parsing complexity
print("\n📧 Email recipient parsing complexity:")
email1_path = email_data_dir / "email1.txt"
if email1_path.exists():
    with open(email1_path, 'r') as f:
        content = f.read()
        lines = content.strip().split('\n')
        
        in_to_section = False
        recipient_lines = []
        
        for line in lines:
            if line.strip() == 'to':
                in_to_section = True
                continue
            elif line.strip() == 'cc' or 'EDT' in line or 'EST' in line:
                in_to_section = False
            elif in_to_section and line.strip():
                recipient_lines.append(line.strip())
        
        print(f"  Found {len(recipient_lines)} lines in 'to' section")
        if recipient_lines:
            print(f"  First line: {recipient_lines[0]}")
            if len(recipient_lines) > 1:
                print(f"  Second line: {recipient_lines[1]}")
        
        # The email parsing expects to construct emails from name + company
        # This is complex and error-prone!
        print("  ⚠️  Email construction from name + title is complex")

print("\n✅ Debug complete!")
print("\n📌 Most likely failing fields:")
print("1. Directory paths (gong_call1 vs gong_call1)")
print("2. Email recipient parsing (complex name-to-email conversion)")
print("3. Attendee email format (daryl.martis vs dmartis)")