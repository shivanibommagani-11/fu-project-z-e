"""
Contract Lookup Agent - Handles comprehensive contract information queries.
"""

import logging
from typing import Optional
from app.agents.base import BaseAgent, AgentState
from app.tools.contract_lookup import ContractLookupTool
from app.services.llm import ChatLiteLLM

logger = logging.getLogger(__name__)


class ContractLookupAgent(BaseAgent):
    """Agent specialized in retrieving and presenting comprehensive contract information."""

    name = "ContractLookupAgent"
    role = "Contract Information Specialist"
    description = "Retrieves and presents comprehensive contract details"

    def __init__(self, llm: Optional[ChatLiteLLM] = None):
        super().__init__(llm)
        self.tools = [ContractLookupTool()]

    def execute(self, state: AgentState) -> AgentState:
        """
        Execute contract lookup.

        Args:
            state: Current state with contract identifiers

        Returns:
            Updated state with contract information
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor

        try:
            logger.info(f"[ContractLookupAgent] Executing for {state.user_id}")

            # Extract contract identifiers from entities
            contract_said = state.extracted_entities.get("contract_said") if state.extracted_entities else None
            contract_nbr = state.extracted_entities.get("contract_nbr") if state.extracted_entities else None

            logger.info(f"[ContractLookupAgent] Lookup parameters - said={contract_said}, nbr={contract_nbr}")

            if not contract_said and not contract_nbr:
                logger.warning("[ContractLookupAgent] No contract identifier provided")
                state.messages.append({
                    "role": "assistant",
                    "content": "I need a contract identifier to look up. Please provide either a Contract SAID (6-digit number) or Contract Number."
                })
                return state

            # Execute lookup tool (async) using ThreadPoolExecutor to avoid event loop issues
            tool = next(t for t in self.tools if t.name == "ContractLookupTool")
            with ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(tool.execute(
                        contract_said=contract_said,
                        contract_nbr=contract_nbr
                    ))
                )
                result = future.result(timeout=30)

            logger.info(f"[ContractLookupAgent] Tool result: {result.success}")

            if result.success:
                contract_data = result.data

                # Format comprehensive response
                response = self._format_contract_response(contract_data)

                state.messages.append({
                    "role": "assistant",
                    "content": response
                })

                # Store contract info in team_context for reference
                state.team_context = {
                    "contract_found": True,
                    "contract_said": contract_data.get("basic", {}).get("contract_said"),
                    "contract_nbr": contract_data.get("basic", {}).get("contract_nbr"),
                }

                logger.info(f"[ContractLookupAgent] ✓ Contract lookup successful")
            else:
                error_msg = result.data.get("error", "Unknown error")
                logger.warning(f"[ContractLookupAgent] Lookup failed: {error_msg}")
                state.messages.append({
                    "role": "assistant",
                    "content": f"I couldn't find the contract. {error_msg}\n\nPlease check the Contract SAID or Contract Number and try again."
                })

            return state

        except Exception as e:
            logger.error(f"[ContractLookupAgent] Error: {str(e)}", exc_info=True)
            state.messages.append({
                "role": "assistant",
                "content": f"An error occurred while looking up the contract: {str(e)}"
            })
            return state

    def _format_contract_response(self, contract_data: dict) -> str:
        """Format contract information into a readable response."""
        basic = contract_data.get("basic", {})
        dates = contract_data.get("dates", {})
        termination = contract_data.get("termination", {})
        financial = contract_data.get("financial", {})
        lease = contract_data.get("lease", {})
        tenant = contract_data.get("tenant", {})
        payment_schedule = contract_data.get("payment_schedule", [])

        response = f"""✅ **Contract Found: {basic.get('contract_nbr')} (SAID: {basic.get('contract_said')})**

**Status & Basic Info:**
• Status: {basic.get('status')}
• Amendment Number: {basic.get('amendment_nbr')}
• Active: {'Yes' if basic.get('is_active') else 'No'}

**Key Dates:**
• Execution Date: {dates.get('execution_date')}
• Termination Date: {dates.get('termination_date')}
• Commencement Date: {dates.get('commencement_date')}
• Expiration Date: {dates.get('expiration_date')}
• Option Expiration: {dates.get('option_expiration_date')}

**Termination Information:**
• Code: {termination.get('termination_code')}
• Description: {termination.get('description')}

**Financial Details:**
• Base Rent: {financial.get('base_rent')}
• Annual Rent: {financial.get('annual_rent')}
• Square Footage: {financial.get('square_footage')}
• GL Account: {financial.get('gl_account')}
• Cost Center: {financial.get('cost_center')}
• FAS13 Doc ID: {financial.get('fas13_doc_id')}

**Lease Information:**
• Lease Type: {lease.get('lease_type')}
• Building ID: {lease.get('building_id')}
• Space ID: {lease.get('space_id')}

**Tenant Information:**
• Tenant ID: {tenant.get('tenant_id')}
• Tenant Name: {tenant.get('tenant_name')}
"""

        if payment_schedule:
            response += "\n**Payment Schedule:**\n"
            for i, pmt in enumerate(payment_schedule[:3], 1):  # Show first 3 payments
                response += f"• Payment {i}: {pmt.get('payment_start')} to {pmt.get('payment_end')} - ${pmt.get('amount')} ({pmt.get('frequency')})\n"
            if len(payment_schedule) > 3:
                response += f"• ... and {len(payment_schedule) - 3} more payment records\n"

        response += "\n**What would you like to do with this contract?** I can help you change the execution date, terminate it, or answer any other questions."

        return response
