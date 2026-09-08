"""
Input validation logic for different use cases.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import re

from app.database.models import Contract
from app.api.schemas import ContractTerminationRecord


class ValidationError(Exception):
    """Base validation error."""

    def __init__(self, field: str, message: str, suggestion: Optional[str] = None):
        self.field = field
        self.message = message
        self.suggestion = suggestion
        super().__init__(f"{field}: {message}")


class ExecutionDateValidator:
    """Validator for execution date modifications."""

    @staticmethod
    def validate_contract_said(contract_said: Any, db: Session) -> int:
        """
        Validate and parse CONTRACT_SAID.
        Returns the integer CONTRACT_SAID if valid.
        """
        if contract_said is None:
            raise ValidationError(
                "contract_said",
                "CONTRACT_SAID is required",
                suggestion="Please provide the CONTRACT_SAID for the contract",
            )

        try:
            said = int(contract_said)
        except (ValueError, TypeError):
            raise ValidationError(
                "contract_said",
                f"CONTRACT_SAID must be a number, got '{contract_said}'",
                suggestion="Please provide a valid CONTRACT_SAID (e.g., 365833)",
            )

        # Check if contract exists
        contract = db.query(Contract).filter(Contract.contract_said == said).first()
        if not contract:
            raise ValidationError(
                "contract_said",
                f"Contract with SAID {said} not found",
                suggestion="Please verify the CONTRACT_SAID is correct",
            )

        return said

    @staticmethod
    def validate_date(date_str: Any):
        """
        Validate and parse execution date.
        Accepts DD-MON-YYYY format (e.g., 23-MAR-2016).
        Returns a Python date object if valid.
        """
        if date_str is None:
            raise ValidationError(
                "execution_dt",
                "Execution date is required",
                suggestion="Please provide a date in DD-MON-YYYY format (e.g., 23-MAR-2016)",
            )

        date_str = str(date_str).strip()

        # Validate format: DD-MON-YYYY
        pattern = r"^\d{2}-[A-Z]{3}-\d{4}$"
        if not re.match(pattern, date_str.upper()):
            raise ValidationError(
                "execution_dt",
                f"Date format '{date_str}' is invalid",
                suggestion="Please use DD-MON-YYYY format (e.g., 23-MAR-2016)",
            )

        # Try to parse the date to ensure it's valid
        try:
            parsed_date = datetime.strptime(date_str.upper(), "%d-%b-%Y").date()
        except ValueError:
            raise ValidationError(
                "execution_dt",
                f"'{date_str}' is not a valid date",
                suggestion="Please check the date and try again",
            )

        return parsed_date

    @staticmethod
    def validate_and_get_contract_details(
        contract_said: int, db: Session
    ) -> Dict[str, Any]:
        """
        Get contract details needed for the update.
        Returns dict with contract_nbr, ammendment_nbr.
        """
        contract = db.query(Contract).filter(Contract.contract_said == contract_said).first()

        if not contract:
            raise ValidationError(
                "contract_said",
                f"Contract with SAID {contract_said} not found",
            )

        return {
            "contract_said": contract.contract_said,
            "contract_nbr": contract.contract_nbr,
            "ammendment_nbr": contract.ammendment_nbr,
        }

    @staticmethod
    def validate_execution_date_request(
        contract_said: Any, execution_date: Any, db: Session
    ) -> Dict[str, Any]:
        """
        Validate execution date change request.
        Returns dict with all required parameters for query execution.
        """
        # Validate inputs
        said = ExecutionDateValidator.validate_contract_said(contract_said, db)
        date = ExecutionDateValidator.validate_date(execution_date)

        # Get contract details
        contract_details = ExecutionDateValidator.validate_and_get_contract_details(said, db)

        return {
            **contract_details,
            "execution_dt": date,
        }


class CSVValidator:
    """Validator for bulk termination CSV data."""

    REQUIRED_COLUMNS = {
        "contract_nbr": int,
        "ammendment_nbr": int,
        "contract_said": int,
        "termination_dt": str,
        "termination_code": str,
        "description": str,
        "fas13_doc_id": str,
    }

    VALID_TERMINATION_CODES = {
        "LANDLORD",
        "TENANT",
        "DEFAULT",
        "EXPIRATION",
        "MUTUAL",
        "OTHER",
    }

    @staticmethod
    def validate_csv_columns(data: List[Dict[str, Any]]) -> None:
        """Validate that CSV has all required columns."""
        if not data or len(data) == 0:
            raise ValidationError("csv", "CSV is empty", suggestion="Please upload a CSV with data")

        first_row = data[0]
        for col in CSVValidator.REQUIRED_COLUMNS.keys():
            if col not in first_row:
                raise ValidationError(
                    "csv",
                    f"Missing required column: {col}",
                    suggestion=f"CSV must have a '{col}' column",
                )

    @staticmethod
    def validate_termination_date(date_str: str):
        """Validate termination date in DD-MON-YYYY format. Returns Python date object."""
        date_str = str(date_str).strip().upper()

        pattern = r"^\d{2}-[A-Z]{3}-\d{4}$"
        if not re.match(pattern, date_str):
            raise ValidationError(
                "termination_dt",
                f"Invalid date format: {date_str}",
                suggestion="Use DD-MON-YYYY format (e.g., 12-JUN-2026)",
            )

        try:
            parsed_date = datetime.strptime(date_str, "%d-%b-%Y")
            if parsed_date <= datetime.now():
                raise ValidationError(
                    "termination_dt",
                    f"Termination date must be in the future",
                    suggestion="Please use a future date",
                )
            return parsed_date.date()
        except ValueError:
            raise ValidationError(
                "termination_dt",
                f"'{date_str}' is not a valid date",
            )

    @staticmethod
    def validate_termination_code(code: str) -> str:
        """Validate termination code."""
        code = str(code).strip().upper()

        if code not in CSVValidator.VALID_TERMINATION_CODES:
            raise ValidationError(
                "termination_code",
                f"Invalid termination code: {code}",
                suggestion=f"Valid codes are: {', '.join(CSVValidator.VALID_TERMINATION_CODES)}",
            )

        return code

    @staticmethod
    def validate_contract_exists(contract_said: int, db: Session) -> Contract:
        """Validate that contract exists in database."""
        contract = db.query(Contract).filter(Contract.contract_said == contract_said).first()

        if not contract:
            raise ValidationError(
                "contract_said",
                f"Contract with SAID {contract_said} not found",
                suggestion="Please verify the contract number",
            )

        return contract

    @staticmethod
    def validate_csv_records(
        records: List[Dict[str, Any]], db: Session
    ) -> List[ContractTerminationRecord]:
        """
        Validate all CSV records.
        Returns list of validated ContractTerminationRecord objects.
        """
        if not records or len(records) == 0:
            raise ValidationError(
                "csv_records",
                "No records to process",
                suggestion="CSV must contain at least one data row",
            )

        validated_records = []
        errors = []

        for idx, record in enumerate(records, start=1):
            try:
                # Sanitize and validate record
                if not isinstance(record, dict):
                    raise ValidationError(
                        "record",
                        f"Row {idx}: Record is not in valid format",
                        suggestion="Each CSV row must be a valid data record",
                    )

                # Validate contract IDs
                try:
                    contract_said = int(record.get("contract_said", 0))
                    contract_nbr = int(record.get("contract_nbr", 0))
                    ammendment_nbr = int(record.get("ammendment_nbr", 0))

                    if contract_said <= 0 or contract_nbr <= 0:
                        raise ValidationError(
                            "contract_id",
                            f"Row {idx}: Invalid contract IDs (must be positive numbers)",
                        )
                except (ValueError, TypeError):
                    raise ValidationError(
                        "contract_id",
                        f"Row {idx}: Contract IDs must be numeric",
                        suggestion="Check contract_said, contract_nbr, and ammendment_nbr are numbers",
                    )

                # Validate contract exists
                contract = CSVValidator.validate_contract_exists(contract_said, db)

                # Validate dates and codes
                term_dt = CSVValidator.validate_termination_date(record.get("termination_dt", ""))
                term_code = CSVValidator.validate_termination_code(
                    record.get("termination_code", "")
                )
                description = str(record.get("description", "")).strip()
                fas13_doc_id = str(record.get("fas13_doc_id", "NOREQ")).strip()

                if not description or len(description) == 0:
                    raise ValidationError(
                        "description", "Description cannot be empty", suggestion="Please provide a termination reason"
                    )

                if len(description) > 500:
                    raise ValidationError(
                        "description",
                        "Description is too long (max 500 characters)",
                        suggestion="Please shorten the description",
                    )

                # Create validated record
                # Convert date object back to string format for Pydantic model
                term_dt_str = term_dt.strftime("%d-%b-%Y") if hasattr(term_dt, 'strftime') else str(term_dt)

                validated_record = ContractTerminationRecord(
                    contract_nbr=contract_nbr,
                    ammendment_nbr=ammendment_nbr,
                    contract_said=contract_said,
                    termination_dt=term_dt_str,
                    termination_code=term_code,
                    description=description,
                    fas13_doc_id=fas13_doc_id,
                )

                validated_records.append(validated_record)

            except ValidationError as e:
                errors.append(
                    {
                        "row": idx,
                        "field": e.field,
                        "error": e.message,
                        "suggestion": e.suggestion,
                    }
                )
            except Exception as e:
                errors.append(
                    {
                        "row": idx,
                        "field": "unknown",
                        "error": f"Unexpected error: {str(e)[:100]}",
                        "suggestion": "Check this row's data format",
                    }
                )

        if errors:
            error_summary = "\n".join(
                [f"  Row {e['row']}: {e['field']} - {e['error']}" for e in errors[:10]]
            )
            if len(errors) > 10:
                error_summary += f"\n  ... and {len(errors) - 10} more errors"

            raise ValidationError(
                "csv_validation",
                f"CSV validation failed:\n{error_summary}",
                suggestion="Please check the CSV data and correct any issues",
            )

        return validated_records
