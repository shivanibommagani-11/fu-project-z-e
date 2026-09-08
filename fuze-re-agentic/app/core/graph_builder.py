"""
LangGraph state graph builder for agent orchestration.
"""

import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END

from app.agents.base import AgentState
from app.agents.orchestrator import OrchestratorAgent
from app.agents.contract import ContractAgent
from app.agents.bulk_agents.contracts import BulkContractTerminationAgent
from app.agents.contract_lookup import ContractLookupAgent
from app.api.templates import GENERAL_QUERY_RESPONSE_PROMPT
from app.services.llm import get_llm_service
from app.database.session import SessionLocal

logger = logging.getLogger(__name__)


class AgentGraphBuilder:
    """Builds and manages the LangGraph state graph for agent orchestration."""

    @staticmethod
    def _should_route_to_contract_agent(state: AgentState) -> bool:
        """Route to ContractAgent if intent is execution_date_change or single_termination."""
        intent = state.current_intent
        return intent in ["execution_date_change", "single_termination"]

    @staticmethod
    def _should_route_to_bulk_agent(state: AgentState) -> bool:
        """Route to BulkTerminationAgent if intent is bulk_termination."""
        intent = state.current_intent
        return intent == "bulk_termination"

    @staticmethod
    def _should_route_to_contract_lookup_agent(state: AgentState) -> bool:
        """Route to ContractLookupAgent if intent is contract_lookup."""
        intent = state.current_intent
        return intent == "contract_lookup"

    @staticmethod
    def _should_route_to_general_query_handler(state: AgentState) -> bool:
        """Route to general query handler if intent is general_query."""
        intent = state.current_intent
        return intent == "general_query"

    @staticmethod
    def _should_continue(state: AgentState) -> bool:
        """Determine if conversation should continue."""
        return state.current_intent not in ["clarification_needed", None]

    @staticmethod
    def _route_from_intent(state: AgentState) -> str:
        """Resolve next node using existing intent-to-agent mapping."""
        if AgentGraphBuilder._should_route_to_contract_agent(state):
            return "contract_agent"
        if AgentGraphBuilder._should_route_to_bulk_agent(state):
            return "bulk_agent"
        if AgentGraphBuilder._should_route_to_contract_lookup_agent(state):
            return "contract_lookup_agent"
        if AgentGraphBuilder._should_route_to_general_query_handler(state):
            return "general_query_agent"
        return END

    @staticmethod
    def orchestrator_node(state: AgentState) -> Dict[str, Any]:
        """Orchestrator agent node."""
        logger.info("[GRAPH] === Orchestrator Node START ===")
        logger.info(f"[GRAPH] Orchestrator - input messages: {len(state.messages)}")
        logger.info(f"[GRAPH] Orchestrator - current_intent: {state.current_intent}")

        llm = get_llm_service()
        logger.info(f"[GRAPH] Orchestrator - LLM service obtained: {llm.model if hasattr(llm, 'model') else 'unknown'}")

        agent = OrchestratorAgent(llm=llm)
        logger.info(f"[GRAPH] Orchestrator - agent created: {agent.name}")

        updated_state = agent.execute(state)

        logger.info(f"[GRAPH] Orchestrator - output messages: {len(updated_state.messages)}")
        logger.info(f"[GRAPH] Orchestrator - output intent: {updated_state.current_intent}")
        logger.info("[GRAPH] === Orchestrator Node END ===")

        return updated_state.dict()

    @staticmethod
    def contract_agent_node(state: AgentState) -> Dict[str, Any]:
        """Contract agent node."""
        logger.info("[GRAPH] === Contract Agent Node START ===")
        logger.info(f"[GRAPH] ContractAgent - input intent: {state.current_intent}")
        logger.info(f"[GRAPH] ContractAgent - input entities: {state.extracted_entities}")
        logger.info(f"[GRAPH] ContractAgent - input messages: {len(state.messages)}")

        llm = get_llm_service()
        logger.info(f"[GRAPH] ContractAgent - LLM service obtained: {llm.model if hasattr(llm, 'model') else 'unknown'}")

        agent = ContractAgent(llm=llm)
        logger.info(f"[GRAPH] ContractAgent - agent created: {agent.name}")

        updated_state = agent.execute(state)

        logger.info(f"[GRAPH] ContractAgent - output messages: {len(updated_state.messages)}")
        logger.info("[GRAPH] === Contract Agent Node END ===")

        return updated_state.dict()

    @staticmethod
    def bulk_termination_agent_node(state: AgentState) -> Dict[str, Any]:
        """Bulk termination agent node."""
        logger.info("[GRAPH] === Bulk Termination Agent Node START ===")
        logger.info(f"[GRAPH] BulkAgent - input intent: {state.current_intent}")
        logger.info(f"[GRAPH] BulkAgent - input entities: {state.extracted_entities}")
        logger.info(f"[GRAPH] BulkAgent - input messages: {len(state.messages)}")

        llm = get_llm_service()
        logger.info(f"[GRAPH] BulkAgent - LLM service obtained: {llm.model if hasattr(llm, 'model') else 'unknown'}")

        agent = BulkContractTerminationAgent(llm=llm)
        logger.info(f"[GRAPH] BulkAgent - agent created: {agent.name}")

        updated_state = agent.execute(state)

        logger.info(f"[GRAPH] BulkAgent - output messages: {len(updated_state.messages)}")
        logger.info("[GRAPH] === Bulk Termination Agent Node END ===")

        return updated_state.dict()

    @staticmethod
    def contract_lookup_agent_node(state: AgentState) -> Dict[str, Any]:
        """Contract lookup agent node."""
        logger.info("[GRAPH] === Contract Lookup Agent Node START ===")
        logger.info(f"[GRAPH] ContractLookupAgent - input intent: {state.current_intent}")
        logger.info(f"[GRAPH] ContractLookupAgent - input entities: {state.extracted_entities}")
        logger.info(f"[GRAPH] ContractLookupAgent - input messages: {len(state.messages)}")

        llm = get_llm_service()
        logger.info(f"[GRAPH] ContractLookupAgent - LLM service obtained: {llm.model if hasattr(llm, 'model') else 'unknown'}")

        agent = ContractLookupAgent(llm=llm)
        logger.info(f"[GRAPH] ContractLookupAgent - agent created: {agent.name}")

        updated_state = agent.execute(state)

        logger.info(f"[GRAPH] ContractLookupAgent - output messages: {len(updated_state.messages)}")
        logger.info("[GRAPH] === Contract Lookup Agent Node END ===")

        return updated_state.dict()

    @staticmethod
    def general_query_agent_node(state: AgentState) -> Dict[str, Any]:
        """General query agent node - handles contract lookups and questions with LLM."""
        logger.info("[GRAPH] === General Query Agent Node START ===")
        logger.info(f"[GRAPH] GeneralQueryAgent - input intent: {state.current_intent}")
        logger.info(f"[GRAPH] GeneralQueryAgent - input entities: {state.extracted_entities}")
        logger.info(f"[GRAPH] GeneralQueryAgent - input messages: {len(state.messages)}")

        from app.database.models import Contract

        llm = get_llm_service()
        db = SessionLocal()
        logger.info(f"[GRAPH] GeneralQueryAgent - database session created")

        try:
            # Extract entities from state
            said = state.extracted_entities.get("contract_said") if state.extracted_entities else None
            query_text = state.extracted_entities.get("query_text", "") if state.extracted_entities else ""

            logger.info(f"[GRAPH] GeneralQueryAgent - contract_said: {said}, query: {query_text[:60]}...")

            # Fallback: Try to extract contract number from query if not in entities
            if not said and query_text:
                import re
                match = re.search(r'\b(\d{5,6})\b', query_text)
                if match:
                    said = match.group(1)
                    logger.info(f"[GRAPH] GeneralQueryAgent - Fallback extracted contract_said: {said} from query")

            contract_context = ""
            if said:
                logger.info(f"[GRAPH] GeneralQueryAgent - looking up contract with SAID: {said}")
                try:
                    said_int = int(said)
                    contract = db.query(Contract).filter(Contract.contract_said == said_int).first()
                    if contract:
                        logger.info(f"[GRAPH] GeneralQueryAgent - ✓ contract found: {contract.contract_nbr}")
                        execution_dt = str(getattr(contract, 'execution_dt', 'N/A'))
                        termination_dt = str(getattr(contract, 'termination_dt', 'N/A'))
                        termination_code = str(getattr(contract, 'termination_code', 'N/A'))
                        contract_context = f"\n\n**Found Contract SAID {said}:**\n- Contract Number: {contract.contract_nbr}\n- Execution Date: {execution_dt}\n- Termination Date: {termination_dt}\n- Termination Code: {termination_code}"
                    else:
                        logger.warning(f"[GRAPH] GeneralQueryAgent - Contract with SAID {said} not found in database")
                        contract_context = f"\n\nNote: Contract SAID {said} was not found in the database."
                except ValueError as ve:
                    logger.error(f"[GRAPH] GeneralQueryAgent - Invalid contract SAID format: {said}, error: {ve}")
                except Exception as lookup_error:
                    logger.error(f"[GRAPH] GeneralQueryAgent - Error looking up contract: {lookup_error}", exc_info=True)

            # Use LLM to generate natural, conversational response
            logger.info(f"[GRAPH] GeneralQueryAgent - using LLM to generate natural response")

            # Format conversation context
            recent_messages = state.messages[-3:] if len(state.messages) > 3 else state.messages
            context_str = ""
            for msg in recent_messages:
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")[:80]
                context_str += f"{role}: {content}\n"

            lc_messages = GENERAL_QUERY_RESPONSE_PROMPT.format_messages(
                query_text=query_text,
                contract_context=contract_context,
                conversation_context=context_str,
            )
            llm_messages = llm.format_langchain_messages(lc_messages)

            try:
                logger.info(f"[GRAPH] GeneralQueryAgent - calling LLM service for natural response")
                # Use ThreadPoolExecutor to run async LLM call in separate thread
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        lambda: asyncio.run(
                            llm.get_chat_completion(
                                messages=llm_messages,
                                temperature=0.7
                            )
                        )
                    )
                    response = future.result(timeout=30)
                logger.info(f"[GRAPH] GeneralQueryAgent - LLM response generated: {response[:80]}...")
            except Exception as llm_error:
                logger.error(f"[GRAPH] GeneralQueryAgent - LLM call failed: {str(llm_error)}, using fallback", exc_info=True)
                response = f"I'd be happy to help with your request: {query_text}\n\nI can assist you with finding contracts, changing execution dates, or terminating contracts. What would you like to do?"

            logger.info(f"[GRAPH] GeneralQueryAgent - appending response to messages")
            state.messages.append({
                "role": "assistant",
                "content": response
            })

        except Exception as e:
            logger.error(f"[GRAPH] GeneralQueryAgent - Error in general query handling: {str(e)}", exc_info=True)
            state.messages.append({
                "role": "assistant",
                "content": "I'm here to help! Could you tell me more about what you need?"
            })
        finally:
            logger.info(f"[GRAPH] GeneralQueryAgent - closing database session")
            db.close()

        logger.info(f"[GRAPH] GeneralQueryAgent - output messages: {len(state.messages)}")
        logger.info("[GRAPH] === General Query Agent Node END ===")

        return state.dict()

    @staticmethod
    def build_graph():
        """
        Build the LangGraph state graph.

        Returns:
            Compiled StateGraph
        """
        logger.info("Building agent graph...")

        # Create graph
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("orchestrator", AgentGraphBuilder.orchestrator_node)
        workflow.add_node("contract_agent", AgentGraphBuilder.contract_agent_node)
        workflow.add_node("bulk_agent", AgentGraphBuilder.bulk_termination_agent_node)
        workflow.add_node("contract_lookup_agent", AgentGraphBuilder.contract_lookup_agent_node)
        workflow.add_node("general_query_agent", AgentGraphBuilder.general_query_agent_node)

        # Set entry point
        workflow.set_entry_point("orchestrator")

        # Add conditional edges from orchestrator
        workflow.add_conditional_edges(
            "orchestrator",
            AgentGraphBuilder._route_from_intent,
            {
                "contract_agent": "contract_agent",
                "bulk_agent": "bulk_agent",
                "contract_lookup_agent": "contract_lookup_agent",
                "general_query_agent": "general_query_agent",
                END: END,
            },
        )

        # Edges from worker agents to end
        workflow.add_edge("contract_agent", END)
        workflow.add_edge("bulk_agent", END)
        workflow.add_edge("contract_lookup_agent", END)
        workflow.add_edge("general_query_agent", END)

        # Compile graph (checkpointing handled by ConversationManager)
        graph = workflow.compile()
        logger.info("[OK] Agent graph compiled successfully")

        return graph


def build_agent_graph():
    """Build and return the agent graph."""
    return AgentGraphBuilder.build_graph()


def run_agent_graph(graph, state: AgentState, config: Optional[Dict] = None):
    """
    Run the agent graph with given state.

    Args:
        graph: Compiled StateGraph
        state: AgentState to process
        config: Optional config dict (for future use)

    Returns:
        Final state after graph execution
    """
    logger.info(f"[GRAPH] === RUNNING AGENT GRAPH ===")
    logger.info(f"[GRAPH] Session: {state.session_id}")
    logger.info(f"[GRAPH] User: {state.user_id}")
    logger.info(f"[GRAPH] Messages in state: {len(state.messages)}")

    try:
        logger.info(f"[GRAPH] Invoking graph...")
        logger.info(f"[GRAPH] Graph type: {type(graph)}")

        # Run the graph synchronously
        result = graph.invoke(state.dict())

        logger.info(f"[GRAPH] ✓ Graph invocation returned")
        logger.info(f"[GRAPH] Result keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")

        # Convert back to AgentState
        logger.info(f"[GRAPH] Converting result back to AgentState")
        final_state = AgentState(**result)

        logger.info(f"[GRAPH] ✓ Graph execution completed")
        logger.info(f"[GRAPH] Final state - current_intent: {final_state.current_intent}")
        logger.info(f"[GRAPH] Final state - messages count: {len(final_state.messages)}")
        logger.info(f"[GRAPH] Final state - team_context: {final_state.team_context}")
        logger.info(f"[GRAPH] === GRAPH EXECUTION COMPLETE ===")
        return final_state

    except Exception as e:
        logger.error(f"[GRAPH] ERROR running agent graph: {str(e)}", exc_info=True)
        logger.error(f"[GRAPH] Exception type: {type(e).__name__}")
        # Return state with error message
        state.messages.append(
            {
                "role": "assistant",
                "content": f"An error occurred: {str(e)}",
            }
        )
        logger.error(f"[GRAPH] === GRAPH EXECUTION FAILED ===")
        return state
