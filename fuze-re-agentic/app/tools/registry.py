"""
Global tool registry for all available tools.
"""

from typing import Dict, List
from app.tools.base import BaseTool
from app.tools.execution_date import ExecutionDateTool


class ToolRegistry:
    """Registry for managing all available tools."""

    _tools: Dict[str, BaseTool] = {}

    @classmethod
    def register(cls, tool: BaseTool) -> None:
        """Register a tool in the registry."""
        cls._tools[tool.name] = tool
        print(f"[OK] Registered tool: {tool.name}")

    @classmethod
    def get_tool(cls, name: str) -> BaseTool:
        """Get a tool by name."""
        return cls._tools.get(name)

    @classmethod
    def get_all_tools(cls) -> Dict[str, BaseTool]:
        """Get all registered tools."""
        return cls._tools.copy()

    @classmethod
    def get_tools_list(cls) -> List[BaseTool]:
        """Get list of all registered tools."""
        return list(cls._tools.values())

    @classmethod
    def initialize(cls) -> None:
        """Initialize all tools."""
        # Register execution date tool
        execution_date_tool = ExecutionDateTool()
        cls.register(execution_date_tool)

        # Bulk tools are registered separately in bulk-payments/registry.py


def get_tools() -> List[BaseTool]:
    """Get all available tools."""
    ToolRegistry.initialize()
    return ToolRegistry.get_tools_list()


def get_tool(name: str) -> BaseTool:
    """Get a specific tool by name."""
    return ToolRegistry.get_tool(name)
