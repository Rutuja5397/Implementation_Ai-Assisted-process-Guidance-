"""
BaseAgent — abstract base class for all agents in the multi-agent pipeline.

Every agent:
  - has a unique AGT_ID and VERSION string
  - receives its entire input as a typed dict and returns a typed dict
  - never imports or calls other agents directly
  - never performs database I/O (data comes in via the input dict)
  - raises AgentError on unrecoverable failures so the Orchestrator
    can catch, log, and degrade gracefully
"""

from abc import ABC, abstractmethod
from typing import Any


AGENT_VERSION = "2.0.0"


class AgentError(Exception):
    """Raised when an agent cannot complete its task."""
    def __init__(self, agent_id: str, message: str):
        super().__init__(f"[{agent_id}] {message}")
        self.agent_id = agent_id


class BaseAgent(ABC):
    AGT_ID:  str = "AGT-00"
    VERSION: str = AGENT_VERSION

    def run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Public entry point called by the Orchestrator.
        Wraps _execute() with consistent error handling.
        """
        try:
            return self._execute(payload)
        except AgentError:
            raise
        except Exception as exc:
            raise AgentError(self.AGT_ID, str(exc)) from exc

    @abstractmethod
    def _execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Override in each concrete agent."""
        ...

    @property
    def agent_version_tag(self) -> str:
        return f"{self.AGT_ID}_v{self.VERSION}"
