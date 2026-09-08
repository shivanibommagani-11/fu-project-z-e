"""
Supervisor/Orchestrator Agent - Routes intents to specialized workers.
"""

import logging
import json
import re
from typing import Dict, Any, Optional
from langchain_core.output_parsers import PydanticOutputParser
from app.agents.base import BaseAgent, AgentState
from app.api.templates import (
    SUPERVISOR_SYSTEM_PROMPT,
    SUPERVISOR_CLASSIFICATION_PROMPT,
    IntentClassificationOutput,
)
from app.core.orchestrator import Intent, IntentOrchestrator
from app.services.llm import ChatLiteLLM

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Supervisor agent that routes user intents to appropriate worker agents."""

    name = "OrchestratorAgent"
    role = "Supervisor - Intent Understanding and Routing"
    description = "Routes user intents to specialized worker agents"
    system_prompt = SUPERVISOR_SYSTEM_PROMPT

    def __init__(self, llm: Optional[ChatLiteLLM] = None):
        super().__init__(llm)

    def _format_conversation_context(self, messages: list) -> str:
        """Format conversation history for LLM context."""
        context_msgs = messages[-8:] if len(messages) > 8 else messages
        formatted = ""
        for msg in context_msgs:
            role = msg.get("role", "unknown").upper()
            content = msg.get("content", "")[:180]
            formatted += f"{role}: {content}\n"
        return formatted

    def _format_known_entities(self, entities: Optional[Dict[str, Any]]) -> str:
        """Sanitize known entities before sending to classifier prompt."""
        if not entities:
            return "{}"

        safe_entities = dict(entities)
        if "bulk_records" in safe_entities:
            records = safe_entities.pop("bulk_records")
            safe_entities["bulk_records_count"] = len(records) if isinstance(records, list) else 0

        try:
            return json.dumps(safe_entities, default=str)
        except Exception:
            return "{}"

    def _classify_intent_with_llm(self, user_message: str, state: AgentState) -> IntentClassificationOutput:
        """Classify intent with structured LangChain output and a single retry on parse failure."""
        parser = PydanticOutputParser(pydantic_object=IntentClassificationOutput)

        context = self._format_conversation_context(state.messages)
        known_entities = self._format_known_entities(state.extracted_entities)

        lc_messages = SUPERVISOR_CLASSIFICATION_PROMPT.format_messages(
            user_message=user_message,
            conversation_context=context,
            known_entities=known_entities,
            format_instructions=parser.get_format_instructions(),
        )
        messages_for_llm = self.llm.format_langchain_messages(lc_messages)

        parse_error = None
        for attempt in range(2):
            try:
                logger.info(f"[Orchestrator] Structured classification attempt {attempt + 1}/2")
                response = self.ask_llm(
                    messages=messages_for_llm,
                    system_prompt=SUPERVISOR_SYSTEM_PROMPT,
                    temperature=0.2,
                )
                parsed = parser.parse(response)
                return parsed
            except Exception as err:
                parse_error = err
                logger.warning(
                    f"[Orchestrator] Structured classification parse failed on attempt {attempt + 1}: {err}"
                )

        logger.error(
            "[Orchestrator] Structured classification failed after retry, defaulting to general_query",
            exc_info=True,
        )
        return IntentClassificationOutput(
            intent="general_query",
            parameters={"query_text": user_message, "fallback_reason": str(parse_error)[:160]},
            confidence=0.5,
            reasoning="Structured classification failed after retry",
        )

    def _recover_parameters_from_context(
        self,
        intent_str: str,
        parameters: Dict[str, Any],
        user_message: str,
        state: AgentState,
    ) -> Dict[str, Any]:
        """
        Normalize and recover key parameters from user message and conversation context.
        """
        recovered: Dict[str, Any] = {}

        # 1. Normalize all incoming keys to lowercase
        if parameters:
            for k, v in parameters.items():
                if v is not None:
                    recovered[k.lower()] = v

        # 2. Parse contract_nbr if it's a composite string like "11232 amendment 1"
        contract_raw = str(recovered.get("contract_nbr", ""))
        if contract_raw:
            amd_match = re.search(r"(\d+)\s*(?:amendment|ammendment|amd|a|-)\s*(\d+)", contract_raw, re.IGNORECASE)
            if amd_match:
                recovered["contract_nbr"] = int(amd_match.group(1))
                recovered["ammendment_nbr"] = int(amd_match.group(2))
            else:
                digits_only = re.search(r"\b(\d{4,8})\b", contract_raw)
                if digits_only:
                    recovered["contract_nbr"] = int(digits_only.group(1))

        # 3. Extract contract_nbr from user message if missing or mistakenly extracted as a year (1900-2099)
        current_nbr = recovered.get("contract_nbr")
        if not current_nbr or (isinstance(current_nbr, int) and 1900 <= current_nbr <= 2099):
            explicit_match = re.search(
                r"(?:contract|nbr|number|#)\s*(?:number|nbr|#)?\s*:?\s*(\d{4,8})",
                user_message,
                re.IGNORECASE,
            )
            if explicit_match:
                recovered["contract_nbr"] = int(explicit_match.group(1))
            else:
                clean_msg = re.sub(r"\d{1,2}-[A-Za-z]{3}-\d{4}", "", user_message)
                match = re.search(r"\b(\d{4,8})\b", clean_msg)
                if match:
                    recovered["contract_nbr"] = int(match.group(1))

        # 4. Extract amendment number from message if not already present
        if "ammendment_nbr" not in recovered and "amendment_nbr" not in recovered:
            amd_match = re.search(
                r"(?:amendment|ammendment|amd)\s*(?:number|nbr|#)?\s*:?\s*(\d+)",
                user_message,
                re.IGNORECASE,
            )
            if amd_match:
                recovered["ammendment_nbr"] = int(amd_match.group(1))
            else:
                recovered["ammendment_nbr"] = 0

        # Ensure both alias keys exist as integers
        amm_val = recovered.get("ammendment_nbr", recovered.get("amendment_nbr", 0))
        try:
            amm_int = int(amm_val)
        except (ValueError, TypeError):
            amm_int = 0
        recovered["ammendment_nbr"] = amm_int
        recovered["amendment_nbr"] = amm_int

        # 5. Extract execution date
        if not recovered.get("execution_date") and not recovered.get("execution_dt"):
            dt = IntentOrchestrator.extract_date(user_message)
            if dt:
                recovered["execution_date"] = dt

        return recovered

    def execute(self, state: AgentState) -> AgentState:
        try:
            logger.info(f"[Orchestrator] === ORCHESTRATOR EXECUTE START ===")
            logger.info(f"[Orchestrator] Processing message from user: {state.user_id}")

            user_message = None
            for msg in reversed(state.messages):
                if msg.get("role") == "user":
                    user_message = msg.get("content")
                    break

            if not user_message or not isinstance(user_message, str) or not user_message.strip():
                state.messages.append({
                    "role": "assistant",
                    "content": "I didn't receive a message. Please try again with your request."
                })
                return state

            classification = self._classify_intent_with_llm(user_message, state)
            intent_str = classification.intent.lower()
            parameters = self._recover_parameters_from_context(
                intent_str=intent_str,
                parameters=classification.parameters,
                user_message=user_message,
                state=state,
            )
            confidence = classification.confidence

            intent_map = {
                "execution_date_change": Intent.EXECUTION_DATE_CHANGE,
                "single_termination": Intent.SINGLE_TERMINATION,
                "bulk_termination": Intent.BULK_TERMINATION,
                "contract_lookup": Intent.CONTRACT_LOOKUP,
                "general_query": Intent.GENERAL_QUERY,
            }

            parsed_intent = intent_map.get(intent_str, Intent.GENERAL_QUERY)
            state.current_intent = parsed_intent.value

            if state.extracted_entities and "bulk_records" in state.extracted_entities:
                state.extracted_entities.update(parameters)
            else:
                state.extracted_entities = parameters

            # Handle Execution Date Changes (EXECUTION_DATE_CHANGE)
            if parsed_intent == Intent.EXECUTION_DATE_CHANGE:
                logger.info("[Orchestrator] EXECUTION_DATE_CHANGE intent detected")

                contract_nbr = parameters.get("contract_nbr")
                execution_date = parameters.get("execution_date") or parameters.get("execution_dt")

                missing_fields = []
                if not contract_nbr:
                    missing_fields.append("contract_nbr")
                if not execution_date:
                    missing_fields.append("execution_date")

                if missing_fields:
                    field_descriptions = {
                        "contract_nbr": "Contract Number (e.g., 11232)",
                        "execution_date": "New Execution Date (e.g., 31-Jan-2028)",
                    }
                    missing_descriptions = [field_descriptions.get(f, f) for f in missing_fields]

                    clarification_msg = f"To change the execution date, I need:\n\n"
                    for i, field_desc in enumerate(missing_descriptions, 1):
                        clarification_msg += f"{i}. {field_desc}\n"

                    state.messages.append({"role": "assistant", "content": clarification_msg})
                    state.current_intent = "clarification_needed"
                    return state

                state.team_context = {
                    "intent": parsed_intent.value,
                    "parameters": parameters,
                    "confidence": confidence,
                    "routed_by": "OrchestratorAgent",
                }
                return state

            # Handle General Queries
            state.team_context = {
                "intent": parsed_intent.value,
                "parameters": parameters,
                "confidence": confidence,
                "routed_by": "OrchestratorAgent",
            }
            return state

        except Exception as e:
            logger.error(f"[Orchestrator] ERROR: {str(e)}", exc_info=True)
            state.messages.append({
                "role": "assistant",
                "content": f"An error occurred while processing your request: {str(e)[:100]}"
            })
            return state