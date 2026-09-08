"""
Pydantic request and response models for API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""

    user_id: str = Field(..., description="User ID from authentication context")
    session_id: str = Field(..., description="Unique session identifier")
    message: str = Field(..., min_length=1, description="User message/intent")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None, description="Previous conversation turns"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "cheetma",
                "session_id": "sess_456",
                "message": "Can you change the execution date to 31-Jan-2028 for contract number 11232?",
                "conversation_history": None,
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""

    status: str = Field(..., description="Response status: success, needs_input, error")
    message: str = Field(..., description="Response message to user")
    session_id: str = Field(..., description="Session ID for tracking")
    required_fields: Optional[List[str]] = Field(
        default=None, description="Fields needed from user for completion"
    )
    execution_details: Optional[Dict[str, Any]] = Field(
        default=None, description="Result of executed operation"
    )
    errors: Optional[List[str]] = Field(default=None, description="Error details if any")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Successfully updated execution date for Contract #11232-0",
                "session_id": "sess_456",
                "required_fields": None,
                "execution_details": {
                    "contract_nbr": 11232,
                    "ammendment_nbr": 0,
                    "new_execution_date": "31-Jan-2028",
                    "rows_updated": 1,
                },
                "errors": None,
            }
        }


class ValidationErrorDetail(BaseModel):
    """Validation error details."""

    field: str = Field(..., description="Field with validation error")
    error: str = Field(..., description="Error message")
    suggestion: Optional[str] = Field(default=None, description="Suggestion to fix error")


class ContractTerminationRecord(BaseModel):
    """Single record for bulk termination CSV."""

    contract_nbr: int = Field(..., description="Contract number")
    ammendment_nbr: int = Field(default=0, description="Amendment number")
    contract_said: Optional[int] = Field(default=None, description="Contract SAID")
    termination_dt: str = Field(..., description="Termination date in DD-MON-YYYY format")
    termination_code: str = Field(..., description="Termination code")
    description: str = Field(..., description="Termination description")
    fas13_doc_id: str = Field(default="NOREQ", description="FAS13 document ID")


class BulkTerminationRequest(BaseModel):
    """Request model for bulk termination CSV upload."""

    user_id: str = Field(..., description="User ID")
    session_id: str = Field(..., description="Session ID")
    records: List[ContractTerminationRecord] = Field(..., description="Contract termination records")

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_123",
                "session_id": "sess_456",
                "records": [
                    {
                        "contract_nbr": 223346,
                        "ammendment_nbr": 0,
                        "termination_dt": "12-JUN-2026",
                        "termination_code": "LANDLORD",
                        "description": "Terminated by VZ for default",
                        "fas13_doc_id": "NOREQ",
                    }
                ],
            }
        }


class BulkTerminationResponse(BaseModel):
    """Response model for bulk termination."""

    status: str = Field(..., description="Status: success, partial_success, error")
    message: str = Field(..., description="Response message")
    session_id: str = Field(..., description="Session ID")
    total_records: int = Field(..., description="Total records processed")
    successful_records: int = Field(default=0, description="Successfully processed")
    failed_records: int = Field(default=0, description="Failed records")
    errors: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Details of failed records"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "message": "Successfully terminated 5 contracts",
                "session_id": "sess_456",
                "total_records": 5,
                "successful_records": 5,
                "failed_records": 0,
                "errors": None,
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="API version")