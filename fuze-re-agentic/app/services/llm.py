"""
LiteLLM integration service for connecting to Verizon AI Gateway.
"""

import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
import os
import litellm
try:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
except ImportError:
    from langchain.schema import HumanMessage, AIMessage, SystemMessage, BaseMessage

from app.config.settings import settings

logger = logging.getLogger(__name__)

# Configure LiteLLM to use custom provider
litellm.set_verbose = False


class ChatLiteLLM:
    """LiteLLM chat service for connecting to Verizon AI Gateway."""

    def __init__(self):
        """Initialize LiteLLM service with Vegas credentials."""
        self.gateway_url = settings.litellm_gateway_url
        self.jwt_token = self._normalize_token(settings.litellm_jwt_token)
        self.model = settings.litellm_model
        self.default_temperature = settings.litellm_temperature
        self.default_max_tokens = settings.litellm_max_tokens

        logger.info(f"[OK] Initialized LiteLLM service with model: {self.model}")
        logger.info(f"  Gateway: {self.gateway_url}")
        if not self._is_jwt_like(self.jwt_token):
            logger.warning(
                "LiteLLM token does not look like a JWT (expected 3 dot-separated sections). "
                "Set a valid LITELLM_JWT_TOKEN in .env."
            )

    @staticmethod
    def _normalize_token(token: Optional[str]) -> str:
        """Normalize gateway token text from env-style inputs."""
        if not token:
            return ""

        cleaned = str(token).strip().strip('"').strip("'")
        if cleaned.lower().startswith("bearer "):
            cleaned = cleaned[7:].strip()

        # If token was accidentally provided as a file path in env, try loading it.
        if os.path.isfile(cleaned):
            try:
                cleaned = open(cleaned, "r", encoding="utf-8").read().strip()
            except Exception:
                pass

        return cleaned

    @staticmethod
    def _is_jwt_like(token: str) -> bool:
        """Basic JWT shape validation: header.payload.signature."""
        if not token:
            return False
        parts = token.split(".")
        return len(parts) == 3 and all(bool(part.strip()) for part in parts)

    def _ensure_valid_token(self) -> None:
        """Raise a clear configuration error when token is malformed."""
        if not self._is_jwt_like(self.jwt_token):
            raise ValueError(
                "Invalid LITELLM_JWT_TOKEN format. Expected a JWT in Header.Payload.Signature format. "
                "Update .env with a valid gateway JWT token."
            )

    def validate_configuration(self) -> None:
        """Validate runtime LLM configuration before first request handling."""
        self._ensure_valid_token()

    async def get_chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Get chat completion from LiteLLM/Vegas gateway.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max tokens
            system_prompt: Optional system prompt to prepend

        Returns:
            Response text from the model
        """
        try:
            self._ensure_valid_token()
            # Prepare messages
            formatted_messages = messages.copy()

            # Add system prompt if provided
            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            # Use provided values or defaults
            temp = temperature if temperature is not None else self.default_temperature
            max_tok = max_tokens if max_tokens is not None else self.default_max_tokens

            logger.debug(f"Calling LiteLLM with {len(formatted_messages)} messages")

            # Call LiteLLM with Vegas gateway (OpenAI-compatible endpoint)
            # For custom gateways, use "openai/" prefix to tell litellm the provider
            model_name = f"openai/{self.model}" if not self.model.startswith("openai/") else self.model

            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: litellm.completion(
                    model=model_name,
                    messages=formatted_messages,
                    temperature=temp,
                    max_tokens=max_tok,
                    api_key=self.jwt_token,
                    api_base=self.gateway_url,
                ),
            )

            # Extract response text
            if response and response.choices and len(response.choices) > 0:
                result = response.choices[0].message.content
                logger.debug(f"LiteLLM response: {result[:100]}...")
                return result
            else:
                raise ValueError("No response from LiteLLM")

        except Exception as e:
            logger.error(f"Error calling LiteLLM: {str(e)}", exc_info=True)
            raise

    async def get_streaming_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ):
        """
        Get streaming chat completion from LiteLLM.

        Args:
            messages: List of message dicts
            temperature: Override default temperature
            max_tokens: Override default max tokens
            system_prompt: Optional system prompt

        Yields:
            Chunks of response text as they arrive
        """
        try:
            self._ensure_valid_token()
            # Prepare messages
            formatted_messages = messages.copy()

            if system_prompt:
                formatted_messages.insert(0, {"role": "system", "content": system_prompt})

            temp = temperature if temperature is not None else self.default_temperature
            max_tok = max_tokens if max_tokens is not None else self.default_max_tokens

            logger.debug(f"Starting streaming completion with {len(formatted_messages)} messages")

            # Call LiteLLM with streaming (OpenAI-compatible endpoint)
            model_name = f"openai/{self.model}" if not self.model.startswith("openai/") else self.model

            response = litellm.completion(
                model=model_name,
                messages=formatted_messages,
                temperature=temp,
                max_tokens=max_tok,
                api_key=self.jwt_token,
                api_base=self.gateway_url,
                stream=True,
            )

            # Yield chunks
            for chunk in response:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        yield delta.content

        except Exception as e:
            logger.error(f"Error in streaming completion: {str(e)}", exc_info=True)
            raise

    def get_chat_completion_sync(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Synchronous wrapper for chat completion safe to call from sync agent code."""
        try:
            # If a loop is already running (e.g. inside FastAPI async request),
            # run coroutine in a separate thread.
            asyncio.get_running_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    lambda: asyncio.run(
                        self.get_chat_completion(
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            system_prompt=system_prompt,
                        )
                    )
                )
                return future.result(timeout=60)
        except RuntimeError:
            # No running loop in this thread; run directly.
            return asyncio.run(
                self.get_chat_completion(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    system_prompt=system_prompt,
                )
            )

    def format_langchain_messages(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """
        Convert LangChain message objects to format expected by LiteLLM.

        Args:
            messages: List of LangChain BaseMessage objects

        Returns:
            List of dicts with 'role' and 'content'
        """
        formatted = []

        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                formatted.append({"role": "assistant", "content": msg.content})
            elif isinstance(msg, SystemMessage):
                formatted.append({"role": "system", "content": msg.content})
            else:
                # Generic message
                formatted.append({"role": "user", "content": str(msg.content)})

        return formatted


# Global LLM service instance
_llm_service: Optional[ChatLiteLLM] = None


def get_llm_service() -> ChatLiteLLM:
    """Get global LLM service instance (lazy initialization)."""
    global _llm_service

    if _llm_service is None:
        _llm_service = ChatLiteLLM()

    return _llm_service


async def initialize_llm() -> ChatLiteLLM:
    """Initialize LLM service."""
    service = get_llm_service()
    service.validate_configuration()
    return service
