"""
Generate Gong Agent Architecture Flowchart

This script creates a visual flowchart of the Gong agent architecture
and saves it as architecture-flowchart.png
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
"""

def generate_flowchart():
    """Generate the architecture flowchart as PNG"""
    
    # Create temporary mermaid file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.mmd', delete=False) as f:
        f.write(mermaid_diagram)
        mmd_file = Path(f.name)
    
    try:
        # Output file path
        output_file = Path(__file__).parent / "architecture-flowchart.png"
        
        # Try to use mermaid-cli if available
        try:
            result = subprocess.run([
                'mmdc', 
                '-i', str(mmd_file),
                '-o', str(output_file),
                '-t', 'neutral',
                '-b', 'white'
            ], capture_output=True, text=True, check=True)
            
            print(f"✅ Flowchart generated successfully: {output_file}")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"❌ mermaid-cli not available: {e}")
            
            # Create a placeholder file with instructions
            placeholder_content = f"""
# Gong Agent Architecture Flowchart

This file should contain the visual flowchart for the Gong agent architecture.

## To generate the actual flowchart:

1. Install mermaid-cli: `npm install -g @mermaid-js/mermaid-cli`
2. Run: `mmdc -i flowchart.mmd -o architecture-flowchart.png`

## Mermaid Diagram Source:

```mermaid
{mermaid_diagram.strip()}
```

## Alternative: Use online Mermaid editor

1. Go to https://mermaid.live/
2. Paste the diagram source above
3. Export as PNG
4. Save as architecture-flowchart.png
"""
            
            with open(output_file.with_suffix('.md'), 'w') as f:
                f.write(placeholder_content)
            
            print(f"📝 Created placeholder with instructions: {output_file.with_suffix('.md')}")
            return False
            
    finally:
        # Clean up temporary file
        mmd_file.unlink()

if __name__ == "__main__":
    generate_flowchart()
