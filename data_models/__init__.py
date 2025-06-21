"""
Module: __init__
Type: Internal Module

Purpose:
Data models and validation schemas for Gong platform integration.

Data Flow:
- Input: Configuration parameters, Authentication credentials
- Processing: API interaction
- Output: Processed results

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: models
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
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