#!/usr/bin/env python3
"""
Gong Validation Test Runner
Validates Gong toolkit extraction against ground truth data
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GongDataValidator:
    """Validates Gong data extraction against ground truth"""
    
    def __init__(self):
        self.validation_dir = Path(__file__).parent / "validation"
        self.call_data_dir = self.validation_dir / "gong_call1"
        self.email_data_dir = self.validation_dir / "gong_emails"
        
    def parse_call_info(self, content: str) -> Dict[str, Any]:
        """Parse call info from text content"""
        lines = content.strip().split('\n')
        call_info = {}
        
        current_key = None
        current_value = []
        
        key_mappings = {
            'Call title': 'title',
            'Call time': 'time',
            'Scheduled on': 'scheduled_on',
            'Language': 'language',
            'Account': 'account',
            'Deal': 'deal',
            'Participants': 'participants'
        }
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            if line in key_mappings:
                # Save previous key-value pair
                if current_key:
                    call_info[current_key] = '\n'.join(current_value).strip()
                
                current_key = key_mappings[line]
                current_value = []
                
                # Special handling for participants
                if line == 'Participants':
                    participants = {'postman': [], 'salesforce': []}
                    current_company = None
                    i += 1
                    
                    while i < len(lines):
                        participant_line = lines[i].strip()
                        
                        if participant_line in ['Postman', 'Salesforce']:
                            current_company = participant_line.lower()
                            i += 1
                            continue
                        elif participant_line in key_mappings or not participant_line:
                            i -= 1  # Back up one line
                            break
                        elif current_company and participant_line:
                            # Parse participant info
                            name = participant_line
                            title = ""
                            
                            # Check if next line is a title
                            if i + 1 < len(lines):
                                next_line = lines[i + 1].strip()
                                if next_line and next_line not in ['Postman', 'Salesforce', 'Owner'] and next_line not in key_mappings:
                                    title = next_line
                                    i += 1
                            
                            participants[current_company].append({
                                'name': name,
                                'title': title
                            })
                        
                        i += 1
                    
                    call_info['participants'] = participants
                    current_key = None
            else:
                if current_key:
                    current_value.append(line)
            
            i += 1
        
        # Add the last key-value pair
        if current_key:
            call_info[current_key] = '\n'.join(current_value).strip()
        
        return call_info
    
    def parse_attendees(self, content: str) -> List[str]:
        """Parse attendees from text content"""
        emails = []
        for line in content.strip().split('\n'):
            line = line.strip()
            if line and '@' in line:
                # Split by semicolon if multiple emails on one line
                for email in line.split(';'):
                    email = email.strip()
                    if email:
                        emails.append(email)
        return emails
    
    def parse_transcript(self, content: str) -> Dict[str, Any]:
        """Parse transcript from text content"""
        lines = content.strip().split('\n')
        
        transcript_data = {
            'title': '',
            'segments': []
        }
        
        # First line is usually the title
        if lines:
            transcript_data['title'] = lines[0].strip()
        
        # Parse transcript segments
        current_speaker = None
        current_text = []
        
        for line in lines[1:]:
            # Check if this is a timestamp line (format: HH:MM AM/PM)
            if line and (line[0].isdigit() or line.startswith('Transcript')):
                continue
                
            # Check if this is a speaker line (ends with colon)
            if line and ':' in line and len(line.split(':')[0]) < 30:
                # Save previous segment
                if current_speaker and current_text:
                    transcript_data['segments'].append({
                        'speaker': current_speaker,
                        'text': ' '.join(current_text)
                    })
                
                current_speaker = line.split(':')[0].strip()
                current_text = [':'.join(line.split(':')[1:]).strip()]
            elif current_speaker:
                current_text.append(line.strip())
        
        # Add last segment
        if current_speaker and current_text:
            transcript_data['segments'].append({
                'speaker': current_speaker,
                'text': ' '.join(current_text)
            })
        
        return transcript_data
    
    def load_ground_truth(self):
        """Load all ground truth data"""
        data = {
            'call': {},
            'emails': []
        }
        
        # Load call data
        if self.call_data_dir.exists():
            # Load call info
            callinfo_file = self.call_data_dir / "callinfo.txt"
            if callinfo_file.exists():
                with open(callinfo_file, 'r') as f:
                    data['call']['info'] = self.parse_call_info(f.read())
            
            # Load attendees
            attendees_file = self.call_data_dir / "attendees.txt"
            if attendees_file.exists():
                with open(attendees_file, 'r') as f:
                    data['call']['attendees'] = self.parse_attendees(f.read())
            
            # Load transcript
            transcript_file = self.call_data_dir / "transcript.txt"
            if transcript_file.exists():
                with open(transcript_file, 'r') as f:
                    data['call']['transcript'] = self.parse_transcript(f.read())
            
            # Load interaction stats
            stats_file = self.call_data_dir / "interactionstats.txt"
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    data['call']['interaction_stats'] = f.read().strip()
            
            # Load spotlight
            spotlight_file = self.call_data_dir / "spotlight.txt"  
            if spotlight_file.exists():
                with open(spotlight_file, 'r') as f:
                    data['call']['spotlight'] = f.read().strip()
        
        # Load email data
        if self.email_data_dir.exists():
            for email_file in self.email_data_dir.glob("*.txt"):
                with open(email_file, 'r') as f:
                    content = f.read()
                    # For now, just store raw content
                    data['emails'].append({
                        'filename': email_file.name,
                        'content': content
                    })
        
        return data
    
    def run_validation(self):
        """Run the validation"""
        logger.info("=== Gong Data Validation ===")
        
        # Load ground truth
        logger.info("Loading ground truth data...")
        ground_truth = self.load_ground_truth()
        
        # Display what we found
        logger.info("\nGround Truth Data Summary:")
        logger.info(f"- Call Info: {'✓' if ground_truth['call'].get('info') else '✗'}")
        logger.info(f"- Attendees: {'✓' if ground_truth['call'].get('attendees') else '✗'} " + 
                   f"({len(ground_truth['call'].get('attendees', []))} found)")
        logger.info(f"- Transcript: {'✓' if ground_truth['call'].get('transcript') else '✗'} " +
                   f"({len(ground_truth['call'].get('transcript', {}).get('segments', []))} segments)")
        logger.info(f"- Interaction Stats: {'✓' if ground_truth['call'].get('interaction_stats') else '✗'}")
        logger.info(f"- Spotlight: {'✓' if ground_truth['call'].get('spotlight') else '✗'}")
        logger.info(f"- Emails: {len(ground_truth['emails'])} files")
        
        # Display parsed call info
        if ground_truth['call'].get('info'):
            logger.info("\nParsed Call Information:")
            for key, value in ground_truth['call']['info'].items():
                if key == 'participants':
                    logger.info(f"  {key}:")
                    for company, people in value.items():
                        logger.info(f"    {company}: {len(people)} people")
                        for person in people:
                            logger.info(f"      - {person['name']} ({person['title']})")
                else:
                    logger.info(f"  {key}: {value}")
        
        # Display attendee emails
        if ground_truth['call'].get('attendees'):
            logger.info(f"\nAttendee Emails ({len(ground_truth['call']['attendees'])} total):")
            for email in ground_truth['call']['attendees'][:5]:  # Show first 5
                logger.info(f"  - {email}")
            if len(ground_truth['call']['attendees']) > 5:
                logger.info(f"  ... and {len(ground_truth['call']['attendees']) - 5} more")
        
        # TODO: When we have extracted data from the Gong toolkit, we'll compare it here
        logger.info("\n✅ Ground truth data successfully loaded and parsed")
        logger.info("⚠️  Note: Actual validation against extracted data not yet implemented")
        logger.info("    (Need to integrate with Gong toolkit extraction)")
        
        return ground_truth

if __name__ == "__main__":
    validator = GongDataValidator()
    validator.run_validation()
