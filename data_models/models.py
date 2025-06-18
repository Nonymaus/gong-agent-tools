"""
Gong Data Models

Pydantic models for Gong platform objects based on HAR analysis and API discovery.
These models represent the core data structures used in Gong's API responses.

Generated from: gong-multitab-capture.har analysis
API Endpoints: 232 unique patterns identified
Authentication: JWT-based with Okta SAML integration
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum


class GongPlatformEnum(str, Enum):
    """Gong platform identifiers"""
    OKTA = "Okta"
    GONG = "gong"


class CallTypeEnum(str, Enum):
    """Types of calls in Gong"""
    AUDIO = "audio"
    VIDEO = "video"
    PHONE = "phone"
    MEETING = "meeting"


class DealStageEnum(str, Enum):
    """Deal stages in Gong"""
    PROSPECTING = "prospecting"
    QUALIFICATION = "qualification"
    PROPOSAL = "proposal"
    NEGOTIATION = "negotiation"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


class ActivityTypeEnum(str, Enum):
    """Activity types in Gong"""
    CALL = "call"
    EMAIL = "email"
    MEETING = "meeting"
    TASK = "task"
    NOTE = "note"


# ============================================================================
# Authentication & Session Models
# ============================================================================

class GongJWTPayload(BaseModel):
    """JWT payload structure for Gong authentication tokens"""
    gp: Optional[str] = Field(None, description="Group/Platform identifier (e.g., 'Okta')")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    jti: str = Field(..., description="JWT ID")
    gu: str = Field(..., description="Gong user identifier (email)")
    cell: Optional[str] = Field(None, description="Gong cell identifier (e.g., 'us-14496')")
    
    @field_validator('exp', 'iat')
    @classmethod
    def validate_timestamps(cls, v):
        """Validate timestamp is reasonable"""
        if v < 1000000000 or v > 9999999999:  # Reasonable Unix timestamp range
            raise ValueError("Invalid timestamp")
        return v

    @field_validator('gu')
    @classmethod
    def validate_email(cls, v):
        """Basic email validation"""
        if '@' not in v or '.' not in v:
            raise ValueError("Invalid email format")
        return v


class GongAuthenticationToken(BaseModel):
    """Gong authentication token with decoded JWT information"""
    token_type: str = Field(..., description="Type of token (last_login_jwt, cell_jwt)")
    raw_token: str = Field(..., description="Raw JWT token string")
    payload: GongJWTPayload = Field(..., description="Decoded JWT payload")
    expires_at: datetime = Field(..., description="Token expiration time")
    issued_at: datetime = Field(..., description="Token issued time")
    is_expired: bool = Field(..., description="Whether token is expired")
    cell_id: Optional[str] = Field(None, description="Gong cell identifier")
    user_email: str = Field(..., description="User email from token")
    
    @model_validator(mode='before')
    @classmethod
    def validate_token_consistency(cls, values):
        """Ensure token data is consistent"""
        if isinstance(values, dict):
            payload = values.get('payload')
            if payload:
                values['user_email'] = payload.gu
                values['cell_id'] = payload.cell
                values['expires_at'] = datetime.fromtimestamp(payload.exp)
                values['issued_at'] = datetime.fromtimestamp(payload.iat)
                values['is_expired'] = datetime.now().timestamp() > payload.exp
        return values


class GongSession(BaseModel):
    """Gong session information with authentication details"""
    session_id: str = Field(..., description="Unique session identifier")
    user_email: str = Field(..., description="Authenticated user email")
    cell_id: str = Field(..., description="Gong cell/instance identifier")
    company_id: Optional[str] = Field(None, description="Company identifier")
    workspace_id: Optional[str] = Field(None, description="Workspace identifier")
    authentication_tokens: List[GongAuthenticationToken] = Field(default_factory=list)
    session_cookies: Dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(True, description="Whether session is active")
    
    @field_validator('cell_id')
    @classmethod
    def validate_cell_format(cls, v):
        """Validate cell ID format (e.g., us-14496)"""
        if v and len(v) < 3:  # Allow empty string, but if provided must be ≥3 chars
            raise ValueError("Invalid cell ID format")
        return v


# ============================================================================
# User & Contact Models
# ============================================================================

class GongUser(BaseModel):
    """Gong user/person model"""
    user_id: Optional[str] = Field(None, description="Unique user identifier")
    email: str = Field(..., description="User email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    full_name: Optional[str] = Field(None, description="Full display name")
    title: Optional[str] = Field(None, description="Job title")
    company: Optional[str] = Field(None, description="Company name")
    phone: Optional[str] = Field(None, description="Phone number")
    is_internal: bool = Field(False, description="Whether user is internal to organization")
    is_active: bool = Field(True, description="Whether user is active")
    created_at: Optional[datetime] = Field(None, description="User creation timestamp")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    
    @field_validator('email')
    @classmethod
    def validate_email_format(cls, v):
        """Validate email format"""
        if '@' not in v or '.' not in v.split('@')[1]:
            raise ValueError("Invalid email format")
        return v.lower()


class GongContact(BaseModel):
    """Gong contact/prospect model"""
    contact_id: Optional[str] = Field(None, description="Unique contact identifier")
    email: str = Field(..., description="Contact email address")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    title: Optional[str] = Field(None, description="Job title")
    company: Optional[str] = Field(None, description="Company name")
    phone: Optional[str] = Field(None, description="Phone number")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    account_id: Optional[str] = Field(None, description="Associated account ID")
    lead_source: Optional[str] = Field(None, description="Lead source")
    stage: Optional[str] = Field(None, description="Contact stage")
    score: Optional[float] = Field(None, description="Contact score")
    created_at: Optional[datetime] = Field(None, description="Contact creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


# ============================================================================
# Call & Conversation Models
# ============================================================================

class GongCallParticipant(BaseModel):
    """Participant in a Gong call"""
    user_id: Optional[str] = Field(None, description="User identifier")
    email: str = Field(..., description="Participant email")
    name: Optional[str] = Field(None, description="Participant name")
    is_host: bool = Field(False, description="Whether participant is host")
    is_internal: bool = Field(False, description="Whether participant is internal")
    join_time: Optional[datetime] = Field(None, description="Time participant joined")
    leave_time: Optional[datetime] = Field(None, description="Time participant left")
    talk_time_seconds: Optional[int] = Field(None, description="Total talk time in seconds")


class GongCall(BaseModel):
    """Gong call/conversation model"""
    call_id: str = Field(..., description="Unique call identifier")
    title: Optional[str] = Field(None, description="Call title")
    call_type: CallTypeEnum = Field(..., description="Type of call")
    start_time: datetime = Field(..., description="Call start time")
    end_time: Optional[datetime] = Field(None, description="Call end time")
    duration_seconds: Optional[int] = Field(None, description="Call duration in seconds")
    participants: List[GongCallParticipant] = Field(default_factory=list)
    host_email: Optional[str] = Field(None, description="Host email address")
    recording_url: Optional[str] = Field(None, description="Recording URL")
    transcript_url: Optional[str] = Field(None, description="Transcript URL")
    meeting_url: Optional[str] = Field(None, description="Meeting URL")
    account_id: Optional[str] = Field(None, description="Associated account ID")
    opportunity_id: Optional[str] = Field(None, description="Associated opportunity ID")
    is_processed: bool = Field(False, description="Whether call is processed")
    is_private: bool = Field(False, description="Whether call is private")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @field_validator('duration_seconds')
    @classmethod
    def validate_duration(cls, v):
        """Validate call duration is reasonable"""
        if v is not None and (v < 0 or v > 86400):  # Max 24 hours
            raise ValueError("Invalid call duration")
        return v


class GongTranscriptSegment(BaseModel):
    """Segment of a call transcript"""
    segment_id: Optional[str] = Field(None, description="Segment identifier")
    speaker_email: str = Field(..., description="Speaker email")
    speaker_name: Optional[str] = Field(None, description="Speaker name")
    start_time_seconds: int = Field(..., description="Segment start time in seconds")
    end_time_seconds: int = Field(..., description="Segment end time in seconds")
    text: str = Field(..., description="Transcript text")
    confidence: Optional[float] = Field(None, description="Transcription confidence")
    is_customer: bool = Field(False, description="Whether speaker is customer")


# ============================================================================
# Account & Deal Models
# ============================================================================

class GongAccount(BaseModel):
    """Gong account/company model"""
    account_id: str = Field(..., description="Unique account identifier")
    name: str = Field(..., description="Account name")
    domain: Optional[str] = Field(None, description="Company domain")
    industry: Optional[str] = Field(None, description="Industry")
    size: Optional[str] = Field(None, description="Company size")
    revenue: Optional[float] = Field(None, description="Annual revenue")
    employees: Optional[int] = Field(None, description="Number of employees")
    website: Optional[str] = Field(None, description="Company website")
    phone: Optional[str] = Field(None, description="Company phone")
    address: Optional[str] = Field(None, description="Company address")
    owner_email: Optional[str] = Field(None, description="Account owner email")
    health_score: Optional[float] = Field(None, description="Account health score")
    created_at: Optional[datetime] = Field(None, description="Account creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class GongDeal(BaseModel):
    """Gong deal/opportunity model"""
    deal_id: str = Field(..., description="Unique deal identifier")
    name: str = Field(..., description="Deal name")
    account_id: str = Field(..., description="Associated account ID")
    owner_email: str = Field(..., description="Deal owner email")
    stage: DealStageEnum = Field(..., description="Current deal stage")
    amount: Optional[float] = Field(None, description="Deal amount")
    currency: Optional[str] = Field("USD", description="Deal currency")
    probability: Optional[float] = Field(None, description="Win probability (0-100)")
    close_date: Optional[datetime] = Field(None, description="Expected close date")
    actual_close_date: Optional[datetime] = Field(None, description="Actual close date")
    source: Optional[str] = Field(None, description="Deal source")
    type: Optional[str] = Field(None, description="Deal type")
    description: Optional[str] = Field(None, description="Deal description")
    is_won: bool = Field(False, description="Whether deal is won")
    is_lost: bool = Field(False, description="Whether deal is lost")
    created_at: Optional[datetime] = Field(None, description="Deal creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    @field_validator('probability')
    @classmethod
    def validate_probability(cls, v):
        """Validate probability is between 0 and 100"""
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Probability must be between 0 and 100")
        return v


# ============================================================================
# Activity & Engagement Models
# ============================================================================

class GongActivity(BaseModel):
    """Gong activity model"""
    activity_id: str = Field(..., description="Unique activity identifier")
    type: ActivityTypeEnum = Field(..., description="Activity type")
    subject: Optional[str] = Field(None, description="Activity subject")
    description: Optional[str] = Field(None, description="Activity description")
    account_id: Optional[str] = Field(None, description="Associated account ID")
    contact_id: Optional[str] = Field(None, description="Associated contact ID")
    deal_id: Optional[str] = Field(None, description="Associated deal ID")
    owner_email: str = Field(..., description="Activity owner email")
    participants: List[str] = Field(default_factory=list, description="Participant emails")
    scheduled_at: Optional[datetime] = Field(None, description="Scheduled time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    duration_minutes: Optional[int] = Field(None, description="Duration in minutes")
    is_completed: bool = Field(False, description="Whether activity is completed")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class GongEmailActivity(BaseModel):
    """Gong email activity model"""
    email_id: str = Field(..., description="Unique email identifier")
    subject: str = Field(..., description="Email subject")
    sender_email: str = Field(..., description="Sender email")
    recipient_emails: List[str] = Field(..., description="Recipient emails")
    cc_emails: List[str] = Field(default_factory=list, description="CC emails")
    bcc_emails: List[str] = Field(default_factory=list, description="BCC emails")
    body_text: Optional[str] = Field(None, description="Email body text")
    body_html: Optional[str] = Field(None, description="Email body HTML")
    sent_at: datetime = Field(..., description="Email sent timestamp")
    account_id: Optional[str] = Field(None, description="Associated account ID")
    deal_id: Optional[str] = Field(None, description="Associated deal ID")
    thread_id: Optional[str] = Field(None, description="Email thread ID")
    is_inbound: bool = Field(False, description="Whether email is inbound")
    is_replied: bool = Field(False, description="Whether email was replied to")


# ============================================================================
# Analytics & Metrics Models
# ============================================================================

class GongCallMetrics(BaseModel):
    """Call analytics and metrics"""
    call_id: str = Field(..., description="Associated call ID")
    total_duration_seconds: int = Field(..., description="Total call duration")
    talk_time_seconds: int = Field(..., description="Total talk time")
    customer_talk_time_seconds: int = Field(..., description="Customer talk time")
    rep_talk_time_seconds: int = Field(..., description="Rep talk time")
    silence_time_seconds: int = Field(..., description="Total silence time")
    interruptions_count: int = Field(0, description="Number of interruptions")
    questions_asked: int = Field(0, description="Number of questions asked")
    sentiment_score: Optional[float] = Field(None, description="Overall sentiment score")
    engagement_score: Optional[float] = Field(None, description="Engagement score")
    next_steps_mentioned: bool = Field(False, description="Whether next steps mentioned")
    
    @field_validator('sentiment_score', 'engagement_score')
    @classmethod
    def validate_scores(cls, v):
        """Validate scores are between -1 and 1"""
        if v is not None and (v < -1 or v > 1):
            raise ValueError("Score must be between -1 and 1")
        return v


class GongTeamStats(BaseModel):
    """Team statistics and performance metrics"""
    team_id: Optional[str] = Field(None, description="Team identifier")
    period_start: datetime = Field(..., description="Statistics period start")
    period_end: datetime = Field(..., description="Statistics period end")
    total_calls: int = Field(0, description="Total number of calls")
    total_call_duration_hours: float = Field(0, description="Total call duration in hours")
    average_call_duration_minutes: float = Field(0, description="Average call duration")
    calls_per_rep_per_week: float = Field(0, description="Average calls per rep per week")
    total_deals: int = Field(0, description="Total number of deals")
    deals_won: int = Field(0, description="Number of deals won")
    deals_lost: int = Field(0, description="Number of deals lost")
    win_rate: float = Field(0, description="Win rate percentage")
    average_deal_size: float = Field(0, description="Average deal size")
    
    @field_validator('win_rate')
    @classmethod
    def validate_win_rate(cls, v):
        """Validate win rate is between 0 and 100"""
        if v < 0 or v > 100:
            raise ValueError("Win rate must be between 0 and 100")
        return v


# ============================================================================
# Library & Content Models
# ============================================================================

class GongLibraryItem(BaseModel):
    """Gong library content item"""
    item_id: str = Field(..., description="Unique item identifier")
    name: str = Field(..., description="Item name")
    type: str = Field(..., description="Item type (call, playlist, etc.)")
    folder_id: Optional[str] = Field(None, description="Parent folder ID")
    owner_email: str = Field(..., description="Item owner email")
    description: Optional[str] = Field(None, description="Item description")
    tags: List[str] = Field(default_factory=list, description="Item tags")
    is_public: bool = Field(False, description="Whether item is public")
    is_favorite: bool = Field(False, description="Whether item is favorited")
    view_count: int = Field(0, description="Number of views")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# API Response Models
# ============================================================================

class GongAPIResponse(BaseModel):
    """Generic Gong API response wrapper"""
    success: bool = Field(True, description="Whether request was successful")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = Field(None, description="Request identifier")


class GongPaginatedResponse(BaseModel):
    """Paginated Gong API response"""
    items: List[Dict[str, Any]] = Field(default_factory=list, description="Response items")
    total_count: int = Field(0, description="Total number of items")
    page: int = Field(1, description="Current page number")
    page_size: int = Field(50, description="Items per page")
    has_more: bool = Field(False, description="Whether more pages available")
    next_page_token: Optional[str] = Field(None, description="Next page token")


# ============================================================================
# Export all models
# ============================================================================

__all__ = [
    # Authentication & Session
    'GongJWTPayload',
    'GongAuthenticationToken', 
    'GongSession',
    
    # Users & Contacts
    'GongUser',
    'GongContact',
    
    # Calls & Conversations
    'GongCallParticipant',
    'GongCall',
    'GongTranscriptSegment',
    
    # Accounts & Deals
    'GongAccount',
    'GongDeal',
    
    # Activities & Engagement
    'GongActivity',
    'GongEmailActivity',
    
    # Analytics & Metrics
    'GongCallMetrics',
    'GongTeamStats',
    
    # Library & Content
    'GongLibraryItem',
    
    # API Responses
    'GongAPIResponse',
    'GongPaginatedResponse',
    
    # Enums
    'GongPlatformEnum',
    'CallTypeEnum',
    'DealStageEnum',
    'ActivityTypeEnum'
]