"""
Enhanced data models for improved email recipient handling
Based on recommendations from Andrej Karpathy's analysis
"""
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, validator


class GongEmailRecipient(BaseModel):
    """Enhanced email recipient with full contact details"""
    email: str = Field(..., description="Email address of recipient")
    name: Optional[str] = Field(None, description="Full name of recipient")
    title: Optional[str] = Field(None, description="Job title")
    company: Optional[str] = Field(None, description="Company name")
    recipient_type: Literal["to", "cc", "bcc"] = Field(..., description="Type of recipient")
    
    @validator('email')
    def validate_email(cls, v):
        """Basic email validation"""
        if '@' not in v:
            # If it's not an email, it might be a name - that's OK for flexibility
            pass
        return v


class GongCallParticipant(BaseModel):
    """Enhanced call participant with company grouping"""
    email: str = Field(..., description="Participant email")
    name: Optional[str] = Field(None, description="Participant name")
    title: Optional[str] = Field(None, description="Job title")
    company: Optional[str] = Field(None, description="Company name")
    is_organizer: bool = Field(False, description="Whether this participant organized the call")
    attendance_status: Optional[Literal["attended", "invited", "declined"]] = Field(None)
    speaking_time: Optional[int] = Field(None, description="Speaking time in seconds")


class GongCallParticipantGroup(BaseModel):
    """Group of participants by company"""
    company: str = Field(..., description="Company name")
    participants: List[GongCallParticipant] = Field(default_factory=list)
    is_account_side: bool = Field(False, description="Whether this is the customer/account side")


class GongEnhancedEmailActivity(BaseModel):
    """Enhanced email activity with full recipient details"""
    # Core fields
    email_id: str = Field(..., description="Unique email identifier")
    thread_id: Optional[str] = Field(None, description="Email thread identifier")
    subject: str = Field(..., description="Email subject line")
    timestamp: Optional[str] = Field(None, description="Email timestamp")
    body: str = Field("", description="Email body content")
    
    # Enhanced sender info
    sender_email: str = Field(..., description="Sender email address")
    sender_name: Optional[str] = Field(None, description="Sender name")
    sender_title: Optional[str] = Field(None, description="Sender job title")
    sender_company: Optional[str] = Field(None, description="Sender company")
    
    # Enhanced recipient info
    recipients: List[GongEmailRecipient] = Field(default_factory=list, description="All recipients with full details")
    
    # Compatibility fields for existing validation
    recipient_emails: List[str] = Field(default_factory=list, description="Just email addresses for compatibility")
    cc_emails: List[str] = Field(default_factory=list, description="CC email addresses for compatibility")
    
    # Email metadata
    message_id: Optional[str] = Field(None, description="Email message ID")
    in_reply_to: Optional[str] = Field(None, description="ID of email this is replying to")
    references: List[str] = Field(default_factory=list, description="Referenced message IDs")
    
    def __post_init__(self):
        """Auto-populate compatibility fields from enhanced recipients"""
        if self.recipients and not self.recipient_emails:
            self.recipient_emails = [r.email for r in self.recipients if r.recipient_type == "to"]
            self.cc_emails = [r.email for r in self.recipients if r.recipient_type == "cc"]


class GongEnhancedCall(BaseModel):
    """Enhanced call model with participant grouping"""
    # Core fields
    call_id: str = Field(..., description="Unique call identifier")
    title: str = Field(..., description="Call title")
    scheduled_time: Optional[str] = Field(None, description="Scheduled time")
    actual_start_time: Optional[str] = Field(None, description="Actual start time")
    duration: Optional[int] = Field(None, description="Call duration in minutes")
    
    # Enhanced participants
    participant_groups: List[GongCallParticipantGroup] = Field(default_factory=list, description="Participants grouped by company")
    all_participants: List[GongCallParticipant] = Field(default_factory=list, description="All participants")
    
    # Call metadata
    platform: Optional[str] = Field(None, description="Platform used (Zoom, Teams, etc.)")
    recording_url: Optional[str] = Field(None, description="Recording URL")
    transcript_available: bool = Field(False, description="Whether transcript is available")
    
    # Spotlight data
    key_moments: List[str] = Field(default_factory=list, description="Key moments/highlights")
    action_items: List[str] = Field(default_factory=list, description="Action items identified")
    
    # Compatibility fields
    attendees: List[str] = Field(default_factory=list, description="Attendee emails for compatibility")
    
    def __post_init__(self):
        """Auto-populate compatibility fields"""
        if self.all_participants and not self.attendees:
            self.attendees = [p.email for p in self.all_participants]


# Validation helpers
class EnhancedValidationResult(BaseModel):
    """Enhanced validation result with more context"""
    field_name: str
    expected_value: str
    actual_value: str
    is_match: bool
    confidence_score: float = Field(default=1.0, description="Confidence in the match (0-1)")
    match_type: Optional[Literal["exact", "fuzzy", "partial", "constructed"]] = Field(None)
    error_message: str = ""