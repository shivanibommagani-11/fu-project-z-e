"""
Streaming chat endpoints with real-time thinking process and execution metadata.
"""

import logging
import json
import asyncio
import re
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.database.session import get_db, SessionLocal
from app.core.conversations import ConversationManager
from app.core.graph_builder import build_agent_graph, run_agent_graph
from app.agents.base import AgentState
from app.agents.orchestrator import OrchestratorAgent
from app.services.llm import get_llm_service
from app.api.templates import GENERAL_QUERY_RESPONSE_PROMPT
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat_stream"])

_agent_graph = None


def _extract_latest_assistant_message(messages):
    for msg in reversed(messages):
        if msg.get("role") == "assistant":
            return msg.get("content", "")
    return ""


def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph


async def chat_stream_generator(user_id: str, session_id: str, user_message: str, db: Session):
    try:
        yield f"data: {json.dumps({'type': 'thinking', 'text': 'Analyzing your request...', 'stage': 'init'})}\n\n"
        await asyncio.sleep(0.2)

        session = ConversationManager.get_session(session_id)
        if not session:
            ConversationManager.create_session(session_id, user_id)

        ConversationManager.add_message(session_id, "user", user_message)
        messages = ConversationManager.get_messages(session_id)

        yield f"data: {json.dumps({'type': 'thinking', 'text': 'Detecting intent and understanding context...', 'stage': 'intent'})}\n\n"
        await asyncio.sleep(0.2)

        state = AgentState(
            user_id=user_id,
            session_id=session_id,
            messages=messages,
            conversation_history=None,
            team_context=None,
            current_intent=None,
            extracted_entities=None,
        )

        llm = get_llm_service()
        orchestrator = OrchestratorAgent(llm=llm)

        yield f"data: {json.dumps({'type': 'thinking', 'text': 'Routing to appropriate agent...', 'stage': 'routing'})}\n\n"
        await asyncio.sleep(0.2)

        routed_state = orchestrator.execute(state)

        if routed_state.current_intent == "general_query":
            yield f"data: {json.dumps({'type': 'thinking', 'text': 'Generating response...', 'stage': 'respond'})}\n\n"

            # Prepare general query prompt
            prompt_inputs = {
                "query_text": user_message,
                "contract_context": "",
                "conversation_context": "",
            }
            lc_messages = GENERAL_QUERY_RESPONSE_PROMPT.format_messages(**prompt_inputs)
            llm_messages = llm.format_langchain_messages(lc_messages)

            accumulated = ""
            async for token in llm.get_streaming_completion(messages=llm_messages, temperature=0.7):
                accumulated += token
                yield f"data: {json.dumps({'type': 'response_delta', 'delta': token, 'text': accumulated})}\n\n"

            ConversationManager.add_message(session_id, "assistant", accumulated)
            yield f"data: {json.dumps({'type': 'done', 'status': 'success'})}\n\n"
            return

        graph = get_agent_graph()
        final_state = run_agent_graph(graph, state)

        yield f"data: {json.dumps({'type': 'thinking', 'text': 'Formatting response...', 'stage': 'format'})}\n\n"
        await asyncio.sleep(0.1)

        response_message = _extract_latest_assistant_message(final_state.messages)
        if not response_message:
            response_message = "I couldn't generate a response. Please try again."

        ConversationManager.add_message(session_id, "assistant", response_message)

        token_chunks = re.findall(r"\S+\s*", response_message) or [response_message]
        accumulated = ""
        for token in token_chunks:
            accumulated += token
            yield f"data: {json.dumps({'type': 'response_delta', 'delta': token, 'text': accumulated})}\n\n"
            await asyncio.sleep(0.02)

        team_context = final_state.team_context or {}
        if team_context.get("execution_details"):
            yield f"data: {json.dumps({'type': 'metadata', 'execution_details': team_context['execution_details']})}\n\n"
        elif team_context.get("template_generated"):
            execution_details = {
                "template_download": {
                    "filename": team_context.get("template_filename", "Bulk_Termination_Template.xlsx"),
                    "url": f"/api/downloads/{team_context.get('template_filename', 'Bulk_Termination_Template.xlsx')}"
                }
            }
            yield f"data: {json.dumps({'type': 'metadata', 'execution_details': execution_details})}\n\n"

        yield f"data: {json.dumps({'type': 'done', 'status': 'success'})}\n\n"

    except Exception as e:
        logger.error(f"[STREAM] Error: {str(e)}", exc_info=True)
        yield f"data: {json.dumps({'type': 'error', 'message': str(e), 'stage': 'error'})}\n\n"


@router.get("/chat/stream")
async def chat_stream(
    user_id: str,
    session_id: str,
    message: str,
    db: Session = Depends(get_db),
):
    return StreamingResponse(
        chat_stream_generator(user_id, session_id, message, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )