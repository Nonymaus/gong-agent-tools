# Gong Agent

This agent integrates with Gong using the GodCapture authentication system.

## Features
- Automatic authentication via GodCapture
- Session management and refresh
- Data extraction capabilities

## Usage
```python
from gong.agent import GongAgent
from _godcapture import GodCapture

godcapture = GodCapture()
agent = GongAgent(godcapture)
await agent.initialize()
```
