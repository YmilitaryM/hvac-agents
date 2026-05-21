"""Shared fixtures and path setup for workorder tests."""
import sys
from pathlib import Path

# Add the agent service to the Python path so we can import agent_service.workorder.*
_agent_svc = Path(__file__).resolve().parents[2] / "services" / "agent"
if str(_agent_svc) not in sys.path:
    sys.path.insert(0, str(_agent_svc))

# Also add the project root so 'src.config' and 'common' resolve
_root = Path(__file__).resolve().parents[2]
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
