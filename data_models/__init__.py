"""
Gong Data Models Package

This package contains Pydantic data models for Gong platform objects.
Models are based on comprehensive HAR analysis of Gong's API endpoints.

Key Features:
- JWT authentication token models with validation
- Core business objects (calls, users, deals, accounts)
- Activity and engagement tracking models
- Analytics and metrics models
- API response wrappers with pagination support

Usage:
    from gong.data_models import GongCall, GongUser, GongDeal
    
    # Create a call object
    call = GongCall(
        call_id="123",
        call_type="video",
        start_time=datetime.now()
    )
"""

from .models import (
    # Authentication & Session
    GongJWTPayload,
    GongAuthenticationToken,
    GongSession,
    
    # Users & Contacts  
    GongUser,
    GongContact,
    
    # Calls & Conversations
    GongCallParticipant,
    GongCall,
    GongTranscriptSegment,
    
    # Accounts & Deals
    GongAccount,
    GongDeal,
    
    # Activities & Engagement
    GongActivity,
    GongEmailActivity,
    
    # Analytics & Metrics
    GongCallMetrics,
    GongTeamStats,
    
    # Library & Content
    GongLibraryItem,
    
    # API Responses
    GongAPIResponse,
    GongPaginatedResponse,
    
    # Enums
    GongPlatformEnum,
    CallTypeEnum,
    DealStageEnum,
    ActivityTypeEnum
)

__version__ = "1.0.0"
__author__ = "CS-Ascension Team"

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