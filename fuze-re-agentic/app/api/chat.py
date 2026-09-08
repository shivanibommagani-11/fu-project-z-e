"""
FastAPI chat endpoints for agentic service.
"""

import logging
import os
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query, Header
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session

from app.api.schemas import ChatRequest, ChatResponse, HealthResponse
from app.agents.base import AgentState
from app.core.graph_builder import build_agent_graph, run_agent_graph
from app.core.conversations import ConversationManager
from app.services.csv_processor import CSVProcessor
from app.core.validators import ValidationError
from app.database.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# Initialize graph singleton
_agent_graph = None


def get_agent_graph():
    """Get or build the agent graph."""
    global _agent_graph
    if _agent_graph is None:
        logger.info("Building agent graph...")
        _agent_graph = build_agent_graph()
    return _agent_graph


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    """
    Process user chat message through agentic workflow.
    """
    try:
        logger.info(f"[Chat] Request from {request.user_id}, session {request.session_id}")

        # Initialize or fetch session
        session = ConversationManager.get_session(request.session_id)
        if not session:
            ConversationManager.create_session(request.session_id, request.user_id)

        # Append user message
        ConversationManager.add_message(request.session_id, "user", request.message)
        messages = ConversationManager.get_messages(request.session_id)

        # Build state
        state = AgentState(
            user_id=request.user_id,
            session_id=request.session_id,
            messages=messages,
            conversation_history=request.conversation_history,
            team_context=None,
            current_intent=None,
            extracted_entities=None,
        )

        # Run agent graph workflow
        graph = get_agent_graph()
        final_state = run_agent_graph(graph, state)

        # Extract latest assistant message
        response_message = ""
        for msg in reversed(final_state.messages):
            if msg.get("role") == "assistant":
                response_message = msg.get("content", "")
                break

        status = "success"
        required_fields = None

        # Extract structured execution results
        team_context = final_state.team_context or {}
        execution_details = team_context.get("execution_details")

        # Handle template download metadata if generated
        if not execution_details and team_context.get("template_generated"):
            execution_details = {
                "template_download": {
                    "filename": team_context.get("template_filename", "Bulk_Termination_Template.xlsx"),
                    "url": f"/api/downloads/{team_context.get('template_filename', 'Bulk_Termination_Template.xlsx')}"
                }
            }

        # Check for missing parameters needing clarification
        if final_state.current_intent == "clarification_needed":
            status = "needs_input"
            intent = team_context.get("intent", "unknown")

            if intent == "execution_date_change":
                required_fields = ["contract_nbr", "execution_date"]
            elif intent == "bulk_termination":
                required_fields = ["csv_file", "termination_date"]

        response = ChatResponse(
            status=status,
            message=response_message,
            session_id=request.session_id,
            required_fields=required_fields,
            execution_details=execution_details,
        )

        logger.info(f"[Chat] Response status: {status}")
        return response

    except ValidationError as e:
        logger.error(f"Validation error: {e.message}")
        return ChatResponse(
            status="error",
            message=f"Validation error: {e.message}",
            session_id=request.session_id,
            required_fields=[e.field],
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error processing request: {str(e)}"
        )

    finally:
        db.close()


@router.post("/chat/upload")
async def chat_upload(
    file: UploadFile = File(...),
    user_id: str = Query(default="demo-user"),
    session_id: str = Query(default="unknown-session"),
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Upload CSV or Excel file for bulk operations.
    """
    try:
        logger.info(f"[Upload] File upload from {user_id}, session {session_id} - File: {file.filename}")

        records = await CSVProcessor.process_bulk_termination_csv(file)
        logger.info(f"[Upload] Processed {len(records)} records from {file.filename}")

        session = ConversationManager.get_session(session_id)
        if not session:
            ConversationManager.create_session(session_id, user_id)

        ConversationManager.set_metadata(session_id, "bulk_records", records)

        upload_message = f"Bulk termination file uploaded with {len(records)} contracts from {file.filename}."
        ConversationManager.add_message(session_id, "system", upload_message)

        messages = ConversationManager.get_messages(session_id)

        state = AgentState(
            user_id=user_id,
            session_id=session_id,
            messages=messages,
            conversation_history=None,
            team_context={
                "intent": "bulk_termination",
                "parameters": {},
            },
            current_intent="bulk_termination",
            extracted_entities={"bulk_records": records},
        )

        graph = get_agent_graph()
        final_state = run_agent_graph(graph, state)

        response_message = ""
        for msg in reversed(final_state.messages):
            if msg.get("role") == "assistant":
                response_message = msg.get("content", "")
                break

        return JSONResponse(
            {
                "status": "success",
                "message": response_message,
                "session_id": session_id,
                "records_processed": len(records),
            }
        )

    except ValidationError as e:
        logger.error(f"Validation error in upload: {e.message}")
        return JSONResponse(
            {
                "status": "error",
                "message": f"Validation error: {e.message}",
                "suggestion": e.suggestion,
                "session_id": session_id,
            },
            status_code=400,
        )

    except Exception as e:
        logger.error(f"Error in upload endpoint: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error processing file: {str(e)}"
        )

    finally:
        db.close()


@router.get("/contract/{contract_said}")
async def lookup_contract(contract_said: int, db: Session = Depends(get_db)):
    """Look up contract details by SAID."""
    try:
        from app.database.models import Contract
        contract = db.query(Contract).filter(Contract.contract_said == contract_said).first()

        if not contract:
            return JSONResponse({
                "status": "error",
                "message": f"Contract with SAID {contract_said} not found."
            }, status_code=404)

        return JSONResponse({
            "status": "success",
            "data": {
                "contract_nbr": contract.contract_nbr,
                "ammendment_nbr": getattr(contract, 'ammendment_nbr', 0),
                "contract_said": contract.contract_said,
                "execution_dt": str(contract.execution_dt) if hasattr(contract, 'execution_dt') else None,
                "termination_dt": str(contract.termination_dt) if hasattr(contract, 'termination_dt') else None,
                "termination_code": getattr(contract, 'termination_code', None),
                "contract_desc": getattr(contract, 'contract_desc', None),
            }
        })
    except Exception as e:
        logger.error(f"Error looking up contract: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": f"Error looking up contract: {str(e)}"
        }, status_code=500)


@router.get("/contracts/search/{query}")
async def search_contracts(query: str, db: Session = Depends(get_db)):
    """Search contracts by contract number or SAID."""
    try:
        from app.database.models import Contract
        results = db.query(Contract).filter(
            (Contract.contract_nbr.cast(db.String).ilike(f"%{query}%")) |
            (Contract.contract_said.cast(db.String).ilike(f"%{query}%"))
        ).limit(10).all()

        if not results:
            return JSONResponse({
                "status": "success",
                "message": f"No contracts found matching '{query}'.",
                "data": []
            })

        contracts = [{
            "contract_nbr": c.contract_nbr,
            "ammendment_nbr": getattr(c, 'ammendment_nbr', 0),
            "contract_said": c.contract_said,
            "execution_dt": str(c.execution_dt) if hasattr(c, 'execution_dt') else None,
        } for c in results]

        return JSONResponse({
            "status": "success",
            "message": f"Found {len(contracts)} contract(s) matching '{query}'.",
            "data": contracts
        })
    except Exception as e:
        logger.error(f"Error searching contracts: {str(e)}")
        return JSONResponse({
            "status": "error",
            "message": f"Error searching contracts: {str(e)}"
        }, status_code=500)


@router.get("/contract/lookup")
async def lookup_contract_comprehensive(said: Optional[int] = None, nbr: Optional[int] = None, db: Session = Depends(get_db)):
    """
    Comprehensive contract lookup by SAID or contract number.
    """
    try:
        from app.tools.contract_lookup import ContractLookupTool

        if not said and not nbr:
            return JSONResponse({
                "status": "error",
                "message": "Must provide either 'said' or 'nbr' query parameter"
            }, status_code=400)

        logger.info(f"[CONTRACT-LOOKUP] Comprehensive lookup - said={said}, nbr={nbr}")

        tool = ContractLookupTool()
        result = tool.execute(
            contract_said=str(said) if said else None,
            contract_nbr=str(nbr) if nbr else None
        )

        if result.success:
            return JSONResponse({
                "status": "success",
                "message": result.message,
                "data": result.data
            })
        else:
            return JSONResponse({
                "status": "error",
                "message": result.message,
                "error": result.data.get("error") if result.data else None
            }, status_code=404)

    except Exception as e:
        logger.error(f"[CONTRACT-LOOKUP] Error: {str(e)}", exc_info=True)
        return JSONResponse({
            "status": "error",
            "message": f"Error looking up contract: {str(e)}"
        }, status_code=500)


@router.get("/downloads/{filename}")
async def download_template(filename: str):
    """Download template or output files."""
    file_path = os.path.join(os.getcwd(), "downloads", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path=file_path, filename=filename)


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version="1.0.0",
    )