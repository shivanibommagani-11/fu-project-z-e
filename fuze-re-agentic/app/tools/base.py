"""
Base tool class for all agent tools.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    """Base input model for tools."""

    pass


class ToolOutput(BaseModel):
    """Base output model for tools."""

    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Result message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Result data")


class BaseTool(ABC):
    """Abstract base class for all tools."""

    name: str = "BaseTool"
    description: str = "Base tool implementation"

    @abstractmethod
    async def execute(self, **kwargs) -> ToolOutput:
        """
        Execute the tool with given parameters.
        Must be implemented by subclasses.
        """
        raise NotImplementedError

    def get_definition(self) -> Dict[str, Any]:
        """
        Get tool definition for LLM integration.
        """
        return {
            "name": self.name,
            "description": self.description,
            "type": "function",
        }
