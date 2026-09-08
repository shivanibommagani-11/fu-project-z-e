"""
Contract Agent - Handles execution date modifications.
"""

import logging
from typing import Dict, Any, Optional
from app.agents.base import BaseAgent, AgentState
from app.tools.execution_date import ExecutionDateTool
from app.api.templates import CONTRACT_AGENT_SYSTEM_PROMPT
from app.services.llm import ChatLiteLLM

logger = logging.getLogger(__name__)


class ContractAgent(BaseAgent):
    """Agent specialized in contract execution date modifications."""

    name = "ContractAgent"
    role = "Contract Specialist - Execution Date Modifications"
    description = "Modifies contract execution dates based on user requests"
    system_prompt = CONTRACT_AGENT_SYSTEM_PROMPT

    def __init__(self, llm: Optional[ChatLiteLLM] = None):
        super().__init__(llm)
        self.tools = [ExecutionDateTool()]

    def execute(self, state: AgentState) -> AgentState:
        """
        Execute contract modification workflow.

        Args:
            state: Current state with extracted entities

        Returns:
            Updated state with result
        """
        try:
            logger.info(f"[ContractAgent] Executing for {state.user_id}")

            intent = state.current_intent
            entities = state.extracted_entities or {}

            if state.team_context is None:
                state.team_context = {}

            # Handle EXECUTION_DATE_CHANGE
            if intent == "execution_date_change":
                contract_nbr = entities.get("contract_nbr")
                ammendment_nbr = (
                    entities.get("ammendment_nbr")
                    if entities.get("ammendment_nbr") is not None
                    else entities.get("amendment_nbr", 0)
                )
                execution_date = entities.get("execution_date") or entities.get("execution_dt")

                logger.info(
                    f"[ContractAgent] Execution date change: NBR={contract_nbr}, AMMENDMENT={ammendment_nbr}, Date={execution_date}"
                )

                tool = self.tools[0]
                result = tool.execute(
                    contract_nbr=contract_nbr,
                    ammendment_nbr=ammendment_nbr,
                    execution_date=execution_date,
                )

                if result.success:
                    state.team_context["execution_details"] = result.data
                    response = (
                        f"✅ **Execution Date Updated Successfully**\n\n"
                        f"**Details:**\n"
                        f"• Contract Number: {result.data.get('contract_nbr', 'N/A')}-{result.data.get('ammendment_nbr', 0)}\n"
                        f"• New Execution Date: {result.data.get('new_execution_date', 'N/A')}\n"
                        f"• Records Updated: {result.data.get('rows_updated', 0)}\n\n"
                        f"The contract execution date has been successfully updated in the system."
                    )
                else:
                    # Populate execution details on database lookup failures
                    state.team_context["execution_details"] = {
                        "contract_nbr": contract_nbr,
                        "ammendment_nbr": ammendment_nbr,
                        "new_execution_date": execution_date,
                        "rows_updated": 0,
                        "error": result.message,
                    }
                    response = (
                        f"❌ **Unable to Update Execution Date**\n\n"
                        f"**Error:** {result.message}\n\n"
                        f"Please try again with the correct contract number and amendment number."
                    )

                state.messages.append({"role": "assistant", "content": response})

            return state

        except Exception as e:
            logger.error(f"[ContractAgent] Error: {str(e)}", exc_info=True)
            state.messages.append(
                {
                    "role": "assistant",
                    "content": f"An error occurred while processing your request: {str(e)}",
                }
            )
            return state