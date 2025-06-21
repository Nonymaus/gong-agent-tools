"""
Module: generate_flowchart
Type: Internal Module

Purpose:
Gong integration component handling specific functionality within the CS-Ascension platform.

Data Flow:
- Input: HTTP requests, Configuration parameters, Authentication credentials
- Processing: Input validation, Data extraction, Data transformation, API interaction
- Output: Error states and exceptions

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: subprocess, tempfile
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
import subprocess
import tempfile
from pathlib import Path

# Mermaid diagram definition
mermaid_diagram = """
graph TD
    A[User Request] --> B{Session Available?}
    B -->|No| C[Session Capture Required]
    B -->|Yes| D[Validate Session]
    
    C --> C1[Browser Navigation]
    C1 --> C2[HAR Capture]
    C2 --> C3[Extract JWT Tokens]
    C3 --> C4[Extract Session Cookies]
    C4 --> C5[Validate Artifacts]
    C5 --> D
    
    D --> E{Session Valid?}
    E -->|No| F[Session Expired]
    E -->|Yes| G[Initialize API Client]
    
    F --> C
    
    G --> H[Determine Request Type]
    H --> I{Data Type?}
    
    I -->|Calls| J[Extract Calls API]
    I -->|Conversations| K[Extract Conversations API]
    I -->|Users| L[Extract Users API]
    I -->|Deals| M[Extract Deals API]
    I -->|Library| N[Extract Library API]
    I -->|Stats| O[Extract Team Stats API]
    I -->|All| P[Extract All Data]
    
    J --> Q[Process Call Data]
    K --> R[Process Conversation Data]
    L --> S[Process User Data]
    M --> T[Process Deal Data]
    N --> U[Process Library Data]
    O --> V[Process Stats Data]
    P --> W[Process All Data Types]
    
    Q --> X[Apply Data Models]
    R --> X
    S --> X
    T --> X
    U --> X
    V --> X
    W --> X
    
    X --> Y[Pydantic Validation]
    Y --> Z{Validation Pass?}
    Z -->|No| AA[Data Quality Error]
    Z -->|Yes| BB[Transform to Standard Format]
    
    BB --> CC[Generate Content Fields]
    CC --> DD[Return Structured Data]
    
    DD --> EE[Validation Framework]
    EE --> FF[Load Ground Truth]
    FF --> GG[Field-by-Field Comparison]
    GG --> HH[Calculate Accuracy]
    HH --> II{Accuracy >= 95%?}
    
    II -->|No| JJ[Validation Failed]
    II -->|Yes| KK[Production Ready]
    
    AA --> LL[Error Handling]
    JJ --> LL
    F --> LL
    
    LL --> MM[Retry Logic]
    MM --> NN{Retry Attempts?}
    NN -->|Available| D
    NN -->|Exhausted| OO[Final Error]
    
    style A fill:#e1f5fe
    style KK fill:#c8e6c9
    style OO fill:#ffcdd2
    style JJ fill:#ffcdd2
    style AA fill:#ffcdd2
    style F fill:#fff3e0
            
            with open(output_file.with_suffix('.md'), 'w') as f:
                f.write(placeholder_content)
            
            print(f"📝 Created placeholder with instructions: {output_file.with_suffix('.md')}")
            return False
            
    finally:
        # Clean up temporary file
        mmd_file.unlink()

if __name__ == "__main__":
    generate_flowchart()
