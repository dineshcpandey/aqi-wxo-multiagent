"""
Base class for all agents in the multi-agent architecture.
Defines standard interface and hooks for logging and error handling.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict

class AgentBase(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input_data and return output_data.
        Must be implemented by all agents.
        """
        pass

    def log(self, message: str):
        # Simple logging hook (can be extended)
        print(f"[{self.name}] {message}")

    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        # Standard error handling
        self.log(f"Error: {str(error)}")
        return {
            "success": False,
            "error": str(error),
            "context": context or {}
        }
