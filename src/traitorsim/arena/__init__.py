"""TraitorSim Arena - Open AI Agent Arena for social deduction gameplay.

This package provides the infrastructure for external AI agents to register,
join games, and compete against each other via HTTP REST APIs.

Key components:
- protocol: Agent protocol specification and validation schemas
- remote_agent: RemoteAgentProxy for communicating with external agents
- engine: GameEngineArena extending the containerized engine for remote play
"""

from .protocol import (
    AgentProtocolVersion,
    AgentRegistration,
    AgentDecisionRequest,
    AgentDecisionResponse,
    validate_vote_response,
    validate_murder_response,
)
from .remote_agent import RemoteAgentProxy
from .engine import GameEngineArena

__all__ = [
    "AgentProtocolVersion",
    "AgentRegistration",
    "AgentDecisionRequest",
    "AgentDecisionResponse",
    "RemoteAgentProxy",
    "GameEngineArena",
    "validate_vote_response",
    "validate_murder_response",
]
