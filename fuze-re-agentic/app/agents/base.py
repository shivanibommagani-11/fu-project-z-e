"""
Base agent class for all agentic workers with LangChain Core & Structured Output support.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Type, TypeVar
from pydantic import BaseModel

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from app.tools.base import BaseTool
from app.services.llm import ChatLiteLLM

T = TypeVar("T", bound=BaseModel)


class AgentState(BaseModel):
    """State object passed between agents in the conversation."""

    user_id: str
    session_id: str
    messages: List[Dict[str, str]]  # Standard message history
    conversation_history: Optional[List[Dict[str, str]]] = None
    team_context: Optional[Dict[str, Any]] = None
    current_intent: Optional[str] = None
    extracted_entities: Optional[Dict[str, Any]] = None

    class Config:
        arbitrary_types_allowed = True

    def to_langchain_messages(self) -> List[BaseMessage]:
        """Convert standard dict messages into LangChain BaseMessage objects."""
        lc_messages = []
        for msg in self.messages:
            role = msg.get("role", "user").lower()
            content = msg.get("content", "")
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))
            else:
                lc_messages.append(HumanMessage(content=content))
        return lc_messages


class BaseAgent(ABC):
    """Abstract base class for all agents with LangChain Core & Structured Output support."""

    name: str = "BaseAgent"
    role: str = "Base Agent Role"
    description: str = "Base agent implementation"
    tools: List[BaseTool] = []
    llm: Optional[ChatLiteLLM] = None
    system_prompt: str = ""

    def __init__(self, llm: Optional[ChatLiteLLM] = None):
        """Initialize agent."""
        self.llm = llm or self._get_default_llm()

    @staticmethod
    def _get_default_llm() -> ChatLiteLLM:
        """Get default LLM service."""
        from app.services.llm import get_llm_service
        return get_llm_service()

    @abstractmethod
    def execute(self, state: AgentState) -> AgentState:
        """Execute agent logic."""
        raise NotImplementedError

    def get_definition(self) -> Dict[str, Any]:
        """Get agent definition for logging/registration."""
        return {
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "tools": [tool.name for tool in self.tools],
        }

    def get_system_prompt(self) -> str:
        """Get agent's system prompt."""
        return self.system_prompt

    def ask_llm(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Ask LLM for completion (synchronous, safe event-loop execution).
        """
        prompt = system_prompt or self.get_system_prompt()
        return self.llm.get_chat_completion_sync(
            messages=messages,
            system_prompt=prompt,
            temperature=temperature
        )

    def invoke_template(
        self,
        prompt_template: ChatPromptTemplate,
        variables: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """
        Format a LangChain ChatPromptTemplate and invoke the LLM synchronously.
        """
        formatted_messages = prompt_template.format_messages(**variables)
        raw_messages = [
            {
                "role": "system" if isinstance(m, SystemMessage) else "assistant" if isinstance(m, AIMessage) else "user",
                "content": str(m.content),
            }
            for m in formatted_messages
        ]

        prompt = system_prompt or self.get_system_prompt()
        return self.llm.get_chat_completion_sync(
            messages=raw_messages, system_prompt=prompt, temperature=temperature
        )

    def invoke_structured(
        self,
        pydantic_schema: Type[T],
        prompt_template: ChatPromptTemplate,
        variables: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = 0.1,
    ) -> T:
        """
        Generate structured output parsed directly into a Pydantic schema using LangChain Core.
        """
        parser = PydanticOutputParser(pydantic_object=pydantic_schema)

        # Inject formatting instructions automatically into variables
        variables_with_format = {
            **variables,
            "format_instructions": parser.get_format_instructions(),
        }

        formatted_messages = prompt_template.format_messages(**variables_with_format)
        raw_messages = [
            {
                "role": "system" if isinstance(m, SystemMessage) else "assistant" if isinstance(m, AIMessage) else "user",
                "content": str(m.content),
            }
            for m in formatted_messages
        ]

        prompt = system_prompt or self.get_system_prompt()
        raw_response = self.llm.get_chat_completion_sync(
            messages=raw_messages, system_prompt=prompt, temperature=temperature
        )

        # Parse directly into the Pydantic model
        return parser.parse(raw_response)

    async def ask_llm_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        """Ask LLM for streaming completion (asynchronous)."""
        prompt = system_prompt or self.get_system_prompt()
        async for chunk in self.llm.get_streaming_completion(
            messages=messages, system_prompt=prompt, temperature=temperature
        ):
            yield chunk

    def __repr__(self):
        return f"<{self.__class__.__name__}(name={self.name})>"