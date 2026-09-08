"""
Bulk Contract Termination Agent - Handles bulk contract terminations.
"""

import logging
from typing import Dict, Any, List, Optional
from app.agents.base import BaseAgent, AgentState
from app.tools.bulk_payments.termination import BulkTerminationTool
from app.tools.bulk_payments.template import BulkTemplateTool 
from app.api.templates import BULK_TERMINATION_AGENT_SYSTEM_PROMPT
from app.services.llm import ChatLiteLLM

logger = logging.getLogger(__name__)


class BulkContractTerminationAgent(BaseAgent):
    """Agent specialized in bulk contract terminations."""

    name = "BulkContractTerminationAgent"
    role = "Bulk Operations Specialist - Contract Terminations"
    description = "Executes bulk termination of multiple contracts"
    system_prompt = BULK_TERMINATION_AGENT_SYSTEM_PROMPT

    def __init__(self, llm: Optional[ChatLiteLLM] = None):
        super().__init__(llm)
        # Give the agent access to both tools
        self.tools = [BulkTerminationTool(), BulkTemplateTool()]

    def execute(self, state: AgentState) -> AgentState:
        """
        Execute bulk termination workflow.

        Args:
            state: Current state with contract records

        Returns:
            Updated state with result
        """
        try:
            logger.info(f"[BulkTerminationAgent] Executing for {state.user_id}")

            # Extract records from state
            records = state.extracted_entities.get("bulk_records") if state.extracted_entities else None

            # Extract termination parameters from first record (same for all records in batch)
            first_record = records[0] if records else {}
            termination_code = str(first_record.get("termination_code", "")).strip() or None
            termination_date = str(first_record.get("termination_dt", "")).strip() or None
            description = str(first_record.get("description", "")).strip() or None
            fas13_doc_id = str(first_record.get("fas13_doc_id", "NOREQ")).strip() or "NOREQ"

            logger.info(
                f"[BulkTerminationAgent] Parameters: {len(records or [])}"
                f" records, code={termination_code}, date={termination_date}"
            )

            # --- MODIFIED: IF NO RECORDS ARE PROVIDED, GENERATE TEMPLATE ---
            logger.info(f"[BulkTerminationAgent] Checking records: records={records}, type={type(records)}, bool={bool(records)}")
            if not records:
                logger.info("[BulkTerminationAgent] No records provided. Generating template.")

                # Generate the template file
                template_tool = next(t for t in self.tools if t.name == "BulkTemplateTool")
                result = template_tool.execute(template_type="termination")

                if result.success:
                    # Get the file path
                    file_path = result.data.get("file_path", "")
                    filename = file_path.split("\\")[-1] if file_path else "Bulk_Termination_Template.xlsx"

                    logger.info(f"[BulkTerminationAgent] Template generated: {filename}")

                    # User-friendly message
                    state.messages.append(
                        {
                            "role": "assistant",
                            "content": (
                                "Perfect! I've prepared a bulk termination template for you. 📋\n\n"
                                "**Your template is ready to download.** It includes all the columns you need:\n"
                                "• contract_nbr - Contract number\n"
                                "• ammendment_nbr - Amendment number\n"
                                "• contract_said - Contract SAID\n"
                                "• termination_dt - Date (format: DD-MON-YYYY)\n"
                                "• termination_code - LANDLORD, TENANT, DEFAULT, etc.\n"
                                "• description - Reason for termination\n"
                                "• fas13_doc_id - FAS13 document ID\n\n"
                                "**Fill it out and upload it back here**, and I'll process the terminations for you! ✅"
                            )
                        }
                    )

                    # Store template info in team_context so chat endpoint can pass it via execution_details
                    state.team_context = {
                        "template_generated": True,
                        "template_filename": filename,
                        "template_path": file_path,
                    }
                    logger.info(f"[BulkTerminationAgent] ✓ team_context set: {state.team_context}")
                else:
                    state.messages.append(
                        {
                            "role": "assistant",
                            "content": "I tried to generate a template for you, but an error occurred. Please try again or contact support."
                        }
                    )
                return state
            # -----------------------------------------------------------------

            # Execute tool (Modified to explicitly fetch the termination tool)
            tool = next(t for t in self.tools if t.name == "BulkTerminationTool")
            result = tool.execute(
                records=records,
                termination_code=termination_code,
                termination_date=termination_date,
                description=description,
                fas13_doc_id=fas13_doc_id,
            )

            logger.info(f"[BulkTerminationAgent] Tool result: {result.success}")

            # Build response message
            if result.success:
                success_count = result.data.get("successful_records", 0)
                total = result.data.get("total_records", 0)
                failed = result.data.get("failed_records", 0)

                response = (
                    f"✅ **Bulk Termination Completed Successfully!**\n\n"
                    f"**Summary:**\n"
                    f"• Total Contracts: {total}\n"
                    f"• Successfully Terminated: {success_count}\n"
                    f"• Failed: {failed}\n\n"
                    f"**Termination Details:**\n"
                    f"• Termination Code: {termination_code}\n"
                    f"• Termination Date: {termination_date}\n"
                    f"• Description: {description}"
                )

                if failed > 0 and result.data.get("errors"):
                    response += f"\n\n⚠️ **Issues Found:**\n"
                    for i, err in enumerate(result.data["errors"][:5], 1):  # Show first 5 errors
                        if isinstance(err, dict):
                            response += f"{i}. {err.get('error', str(err))}\n"
                        else:
                            response += f"{i}. {str(err)}\n"
                    if len(result.data["errors"]) > 5:
                        response += f"... and {len(result.data['errors']) - 5} more errors"

            else:
                response = f"❌ **Bulk Termination Failed**\n\n"
                response += f"**Error:** {result.message}\n\n"

                if result.data:
                    if result.data.get("field"):
                        response += f"**Issue Field:** {result.data['field']}\n"
                        if result.data.get("error"):
                            response += f"**Details:** {result.data.get('error', 'Unknown error')}\n"
                    if result.data.get("suggestion"):
                        response += f"\n**Suggestion:** {result.data['suggestion']}\n"

                response += "\nPlease check your CSV file and try again."

            state.messages.append({"role": "assistant", "content": response})

            return state

        except Exception as e:
            logger.error(f"[BulkTerminationAgent] Error: {str(e)}", exc_info=True)
            state.messages.append(
                {
                    "role": "assistant",
                    "content": f"An error occurred during bulk termination: {str(e)}",
                }
            )
            return state