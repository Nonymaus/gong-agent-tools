# Gong Agent Architecture Flowchart

This file contains the visual flowchart for the Gong agent architecture with **specific tool references**.

## Mermaid Diagram Source:

```mermaid
graph TD
    A[User Request] --> B{Session Available?}
    B -->|No| C[Session Capture Required<br/>📦 _godcapture]
    B -->|Yes| D[Validate Session<br/>📦 agent.py]
    
    C --> C1[Browser Navigation<br/>📦 _godcapture + okta_login]
    C1 --> C2[HAR Capture<br/>📦 _godcapture/core/har_capture.py]
    C2 --> C3[Extract JWT Tokens<br/>📦 _godcapture/plugins/jwt_decoder.py]
    C3 --> C4[Extract Session Cookies<br/>📦 _godcapture/core/har_analyzer.py]
    C4 --> C5[Validate Artifacts<br/>📦 authentication/session_validator.py]
    C5 --> D
    
    D --> E{Session Valid?<br/>📦 authentication/auth_manager.py}
    E -->|No| F[Session Expired]
    E -->|Yes| G[Initialize API Client<br/>📦 api_client/gong_api_client.py]
    
    F --> C6[Reauthenticate<br/>📦 _godcapture.reauthenticate()]
    C6 --> C
    
    G --> H[Determine Request Type<br/>📦 agent.py:extract_data()]
    H --> I{Data Type?}
    
    I -->|Calls| J[Extract Calls API<br/>📦 api_client._extract_calls()]
    I -->|Conversations| K[Extract Conversations API<br/>📦 api_client._extract_conversations()]
    I -->|Users| L[Extract Users API<br/>📦 api_client._extract_users()]
    I -->|Deals| M[Extract Deals API<br/>📦 api_client._extract_deals()]
    I -->|Library| N[Extract Library API<br/>📦 api_client._extract_library()]
    I -->|Stats| O[Extract Team Stats API<br/>📦 api_client._extract_team_stats()]
    I -->|All| P[Extract All Data<br/>📦 agent._extract_comprehensive()]
    
    J --> Q[Process Call Data<br/>📦 data_models/call.py]
    K --> R[Process Conversation Data<br/>📦 data_models/conversation.py]
    L --> S[Process User Data<br/>📦 data_models/user.py]
    M --> T[Process Deal Data<br/>📦 data_models/deal.py]
    N --> U[Process Library Data<br/>📦 data_models/library.py]
    O --> V[Process Stats Data<br/>📦 data_models/stats.py]
    P --> W[Process All Data Types<br/>📦 agent._process_all_data()]
    
    Q --> X[Apply Data Models<br/>📦 data_models/__init__.py]
    R --> X
    S --> X
    T --> X
    U --> X
    V --> X
    W --> X
    
    X --> Y[Pydantic Validation<br/>📦 pydantic BaseModel]
    Y --> Z{Validation Pass?}
    Z -->|No| AA[Data Quality Error<br/>📦 agent.GongAgentError]
    Z -->|Yes| BB[Transform to Standard Format<br/>📦 data_models.to_dict()]
    
    BB --> CC[Generate Content Fields<br/>📦 agent._generate_content()]
    CC --> DD[Return Structured Data]
    
    DD --> EE[Validation Framework<br/>📦 validation/validator.py]
    EE --> FF[Load Ground Truth<br/>📦 run_gong_validation.py]
    FF --> GG[Field-by-Field Comparison<br/>📦 validation/field_validators.py]
    GG --> HH[Calculate Accuracy<br/>📦 validation/accuracy_calculator.py]
    HH --> II{Accuracy >= 95%?}
    
    II -->|No| JJ[Validation Failed]
    II -->|Yes| KK[Production Ready]
    
    AA --> LL[Error Handling<br/>📦 agent._handle_error()]
    JJ --> LL
    F --> LL
    
    LL --> MM[Retry Logic<br/>📦 agent._retry_with_backoff()]
    MM --> NN{Retry Attempts?}
    NN -->|Available| D
    NN -->|Exhausted| OO[Final Error]
    
    style A fill:#e1f5fe
    style KK fill:#c8e6c9
    style OO fill:#ffcdd2
    style JJ fill:#ffcdd2
    style AA fill:#ffcdd2
    style F fill:#fff3e0
    style C fill:#f3e5f5
    style C6 fill:#f3e5f5
```

## Key Tool References:

### 🔐 Authentication & Session Management
- **_godcapture**: Central authentication hub (`app_backend/agent_tools/_godcapture/`)
  - `core/godcapture.py`: Main reauthenticate() method
  - `core/har_capture.py`: HAR file capture
  - `plugins/jwt_decoder.py`: JWT token extraction
  - `adapters/okta_login_adapter.py`: Okta SSO integration

### 📊 Data Extraction
- **agent.py**: Main orchestrator (`app_backend/agent_tools/gong/agent.py`)
  - `extract_data()`: Entry point for all extractions
  - `_extract_comprehensive()`: Parallel extraction coordinator
  
- **api_client/**: API interaction layer
  - `gong_api_client.py`: Main API client with all extraction methods
  - Rate limiting, retries, connection pooling

### 📦 Data Models
- **data_models/**: Pydantic models for validation
  - `call.py`: GongCall model
  - `user.py`: GongUser model  
  - `conversation.py`: GongConversation model
  - etc.

### ✅ Validation
- **validation/**: Validation framework
  - `validator.py`: Main validation logic
  - `field_validators.py`: Field-level validation
  - `accuracy_calculator.py`: Accuracy metrics
  
- **Ground Truth**:
  - `run_gong_validation.py`: Ground truth parser
  - `validation/gong_call1/`: Sample call data
  - `validation/gong_emails/`: Sample email data

### 🚨 Error Handling
- **Retry Logic**: Built into agent.py
- **Session Refresh**: _godcapture.reauthenticate()
- **Rate Limiting**: api_client handles 429s

## Usage for CrewAI:

```python
# Simple usage
from app_backend.agent_tools.gong.agent import GongAgent

agent = GongAgent()

# Extract specific data
data = agent.extract_data({
    'calls': True,
    'users': True
})

# Extract everything
all_data = agent.extract_data({'all': True})

# Session will auto-refresh via _godcapture if needed
```

## Alternative: Generate PNG

1. Go to https://mermaid.live/
2. Paste the diagram source above
3. Export as PNG
4. Save as architecture-flowchart.png
