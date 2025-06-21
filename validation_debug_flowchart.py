#!/usr/bin/env python3
"""
Create a debugging flowchart showing where Gong validation breaks down
"""

def create_validation_debug_flowchart():
    flowchart = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    GONG VALIDATION DEBUGGING FLOWCHART                       ║
║                         By Julia Evans 🔍                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌─────────────────────────────────────┐
│    START: Run Validation Test       │
│ (test_real_data_validation.py etc)  │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Load Ground Truth Data (Lines 77)  │
│  validator.load_ground_truth_*()    │
└──────────────┬──────────────────────┘
               │
               ▼
       ╔═══════════════════╗
       ║ 🚨 FAILURE #1 🚨  ║    ◀── Directory Path Mismatch
       ╠═══════════════════╣
       ║ Looking for:      ║
       ║ • gong_call1 ║        The test files expect these
       ║ • gong_emails║        directory names but they
       ║                   ║        don't exist!
       ║ But actual dirs:  ║
       ║ • gong_call1      ║ ✓
       ║ • gong_emails     ║ ✓
       ╚═══════════════════╝
               │
               │ (If paths were fixed...)
               ▼
┌─────────────────────────────────────┐
│    Parse Ground Truth Files         │
│  • callinfo.txt                     │
│  • attendees.txt                    │
│  • email1.txt, email2.txt           │
└──────────────┬──────────────────────┘
               │
               ▼
       ╔═══════════════════╗
       ║ 🚨 FAILURE #2 🚨  ║    ◀── Email Recipient Parsing
       ╠═══════════════════╣
       ║ Complex parsing:  ║
       ║                   ║        The parser tries to construct
       ║ "Danai Kongkarat" ║        email addresses from names:
       ║ + "..Analyst.."   ║        
       ║ + "Salesforce"    ║        Name → firstname.lastname@company.com
       ║        ↓          ║        
       ║ danai.kongkarat@  ║        This is fragile and error-prone!
       ║ salesforce.com ?? ║
       ╚═══════════════════╝
               │
               ▼
┌─────────────────────────────────────┐
│   Extract Data via Gong Agent       │
│   (Would need fresh session)        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│   Compare Extracted vs Ground Truth │
│   Field-by-field validation         │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│         Calculate Accuracy          │
│    Need >95% field accuracy         │
└──────────────┬──────────────────────┘
               │
               ▼
         ╔═══════════╗
         ║   FAIL    ║
         ║  0% Pass  ║ ◀── Can't even load data!
         ╚═══════════╝

═══════════════════════════════════════════════════════════════════════════════

🔧 FIXES NEEDED:

1. Update test files to use correct directory names:
   - Change: self.call_data_dir = validation_dir / "gong_call1"
   - To:     self.call_data_dir = validation_dir / "gong_call1"
   
   - Change: self.email_data_dir = validation_dir / "gong_emails"  
   - To:     self.email_data_dir = validation_dir / "gong_emails"

2. Improve email parsing logic:
   - Current: Complex name→email construction
   - Better: Look for actual email addresses in the data
   - Or: Make validation more flexible for recipient matching

═══════════════════════════════════════════════════════════════════════════════

📊 CURRENT STATUS:
• Directory issue prevents any data from loading (0% success)
• Even if fixed, email recipient parsing would likely fail
• The VALIDATION_RESULTS.md showing 100% is from a different test!

"""
    return flowchart

if __name__ == "__main__":
    print(create_validation_debug_flowchart())
    
    # Save to file
    with open("VALIDATION_DEBUG_FLOWCHART.txt", "w") as f:
        f.write(create_validation_debug_flowchart())