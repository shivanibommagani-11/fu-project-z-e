"""
Intent orchestrator for parsing user messages and routing to appropriate handlers.
"""

import re
from typing import Optional, Dict, Any, Tuple
from enum import Enum


class Intent(Enum):
    """Supported intents."""

    EXECUTION_DATE_CHANGE = "execution_date_change"
    SINGLE_TERMINATION = "single_termination"
    BULK_TERMINATION = "bulk_termination"
    CONTRACT_LOOKUP = "contract_lookup"
    GENERAL_QUERY = "general_query"
    UNKNOWN = "unknown"


class IntentOrchestrator:
    """
    Compatibility shim for legacy callers.

    Runtime intent recognition is handled by `OrchestratorAgent` via LLM
    structured output. This class is intentionally non-authoritative for
    intent routing decisions.
    """

    # Keywords for intent detection
    EXECUTION_DATE_KEYWORDS = {
        "execution date",
        "execution_date",
        "change date",
        "modify date",
        "update date",
        "execution date change",
        "change execution",
        "update execution date",
    }

    BULK_TERMINATION_KEYWORDS = {
        "bulk",
        "termination",
        "terminate",
        "bulk termination",
        "bulk terminate",
        "csv",
        "upload",
        "bulk contracts",
        "mass termination",
    }

    @staticmethod
    def detect_intent(message: str) -> Intent:
        """
        Legacy method retained for backward compatibility only.

        Intent recognition is LLM-driven in the orchestrator agent. This method
        avoids keyword/regex-based routing decisions and returns GENERAL_QUERY
        when a message exists.
        """
        if not message or not isinstance(message, str) or not message.strip():
            return Intent.UNKNOWN
        return Intent.GENERAL_QUERY

    @staticmethod
    def extract_contract_said(message: str) -> Optional[str]:
        """
        Extract CONTRACT_SAID from message.
        Looks for patterns like "SAID 365833", "contract 128868", etc.
        Returns the SAID if found, or the contract number (which will be converted later).
        """
        if not message or not isinstance(message, str):
            return None

        # FIRST: Look for explicit SAID patterns (highest priority)
        said_patterns = [
            r"(?:SAID|CONTRACT_SAID|contract\s+said)\s*[:=]?\s*(\d+)",
            r"said\s+(\d+)",
            r"SAID\s+(\d+)",
        ]

        for pattern in said_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1)

        # SECOND: Look for contract number patterns
        contract_nbr_patterns = [
            r"contract\s+(?:number|nbr|#)\s*[:=]?\s*(\d+)",
            r"contract\s+(\d{5,6})",  # "contract 128868"
            r"#\s*(\d{5,6})",
            r"\bfor\s+(\d{5,6})",
        ]

        for pattern in contract_nbr_patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                extracted = match.group(1)
                # Validate it's a reasonable SAID (5-6 digits typically)
                if extracted and len(extracted) >= 5:
                    return extracted

        return None

    @staticmethod
    def extract_date(message: str) -> Optional[str]:
        """
        Extract date in DD-MON-YYYY format from message.
        Handles formats: "23-MAR-2016", "12-JUN-2026", "23/MAR/2016", "23 MAR 2016", "24 june 2026", etc.
        Always returns DD-MON-YYYY format if found.
        """
        if not message or not isinstance(message, str):
            return None

        # Month abbreviation mapping
        month_map = {
            'jan': 'JAN', 'january': 'JAN',
            'feb': 'FEB', 'february': 'FEB',
            'mar': 'MAR', 'march': 'MAR',
            'apr': 'APR', 'april': 'APR',
            'may': 'MAY',
            'jun': 'JUN', 'june': 'JUN',
            'jul': 'JUL', 'july': 'JUL',
            'aug': 'AUG', 'august': 'AUG',
            'sep': 'SEP', 'september': 'SEP',
            'oct': 'OCT', 'october': 'OCT',
            'nov': 'NOV', 'november': 'NOV',
            'dec': 'DEC', 'december': 'DEC',
        }

        # Pattern 1: DD-MON-YYYY (hyphenated with 3-letter month)
        pattern1 = r"(\d{1,2})-([A-Z]{3})-(\d{4})"
        match = re.search(pattern1, message, re.IGNORECASE)
        if match:
            day, month, year = match.groups()
            return f"{day.zfill(2)}-{month.upper()}-{year}"

        # Pattern 2: DD/MON/YYYY (slash separated with 3-letter month)
        pattern2 = r"(\d{1,2})/([A-Z]{3})/(\d{4})"
        match = re.search(pattern2, message, re.IGNORECASE)
        if match:
            day, month, year = match.groups()
            return f"{day.zfill(2)}-{month.upper()}-{year}"

        # Pattern 3: DD MON YYYY (space separated with 3-letter month)
        pattern3 = r"(\d{1,2})\s+([A-Z]{3})\s+(\d{4})"
        match = re.search(pattern3, message, re.IGNORECASE)
        if match:
            day, month, year = match.groups()
            return f"{day.zfill(2)}-{month.upper()}-{year}"

        # Pattern 4: DD MONTH YYYY (full month name, space separated)
        pattern4 = r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})"
        match = re.search(pattern4, message)
        if match:
            day, month_text, year = match.groups()
            month_lower = month_text.lower()
            if month_lower in month_map:
                return f"{day.zfill(2)}-{month_map[month_lower]}-{year}"

        return None

    @staticmethod
    def extract_contract_numbers(message: str) -> list:
        """
        Extract contract numbers from message.
        Looks for comma-separated numbers or individual contract number references.
        """
        # Pattern for contract numbers (usually 6 digits)
        pattern = r"contract\s*(?:nbr|number|#)?s?\s*[:\s]*(\d+(?:\s*,\s*\d+)*)"
        matches = re.findall(pattern, message, re.IGNORECASE)

        numbers = []
        for match in matches:
            # Split by comma and extract numbers
            parts = match.split(",")
            numbers.extend([int(p.strip()) for p in parts if p.strip().isdigit()])

        return numbers

    @staticmethod
    def parse_user_input(message: str) -> Dict[str, Any]:
        """
        Parse user input and extract intent and parameters.
        Returns dict with detected intent and extracted parameters.
        """
        intent = IntentOrchestrator.detect_intent(message)

        result = {
            "intent": intent,
            "original_message": message,
            "parameters": {},
            "confidence": 0.0,
        }

        if intent == Intent.EXECUTION_DATE_CHANGE:
            said = IntentOrchestrator.extract_contract_said(message)
            date = IntentOrchestrator.extract_date(message)

            result["parameters"] = {
                "contract_said": said,
                "execution_date": date,
            }

            # Calculate confidence
            missing = sum(1 for v in result["parameters"].values() if v is None)
            result["confidence"] = (2 - missing) / 2  # 0.0 to 1.0

        elif intent == Intent.SINGLE_TERMINATION:
            said = IntentOrchestrator.extract_contract_said(message)
            date = IntentOrchestrator.extract_date(message)

            result["parameters"] = {
                "contract_said": said,
                "termination_date": date,
                "termination_code": None,
                "description": None,
            }

            # Calculate confidence (high if SAID is present)
            result["confidence"] = 0.8 if said else 0.5

        elif intent == Intent.BULK_TERMINATION:
            contract_numbers = IntentOrchestrator.extract_contract_numbers(message)
            date = IntentOrchestrator.extract_date(message)

            result["parameters"] = {
                "contract_numbers": contract_numbers,
                "termination_date": date,
                "expects_csv": "csv" in message.lower() or "upload" in message.lower(),
            }

            result["confidence"] = 0.7 if contract_numbers or date else 0.5

        elif intent == Intent.GENERAL_QUERY:
            said = IntentOrchestrator.extract_contract_said(message)
            result["parameters"] = {
                "contract_said": said,
                "query_text": message,
            }
            result["confidence"] = 0.8 if said else 0.6

        return result
    @staticmethod
    def resolve_contract_id(contract_id: str) -> Optional[str]:
        """
        Resolve contract ID - can be either SAID or contract_nbr.
        First tries to match as SAID, then as contract_nbr.
        Returns the SAID if found, otherwise returns the original ID.
        """
        try:
            from app.database.session import get_db
            from app.database.models import Contract

            contract_num = int(contract_id)
            db = next(get_db())

            # FIRST: Try to find by SAID (preferred)
            contract = db.query(Contract).filter(Contract.contract_said == contract_num).first()
            if contract:
                return str(contract.contract_said)

            # SECOND: Try to find by contract_nbr
            contract = db.query(Contract).filter(Contract.contract_nbr == contract_num).first()
            if contract and hasattr(contract, 'contract_said'):
                return str(contract.contract_said)

            # If not found either way, return original
            return contract_id
        except Exception as e:
            # If lookup fails, return original value
            return contract_id

    @staticmethod
    def get_missing_fields(parsed_input: Dict[str, Any]) -> list:
        """
        Get list of missing required fields for the detected intent.
        """
        intent = parsed_input["intent"]
        parameters = parsed_input["parameters"]
        missing = []

        if intent == Intent.EXECUTION_DATE_CHANGE:
            if not parameters.get("contract_said"):
                missing.append("contract_said")
            if not parameters.get("execution_date"):
                missing.append("execution_date")

        elif intent == Intent.SINGLE_TERMINATION:
            if not parameters.get("contract_said"):
                missing.append("contract_said")
            # Termination date, code, and description are optional - can ask for them

        elif intent == Intent.BULK_TERMINATION:
            if not parameters.get("expects_csv"):
                missing.append("csv_file")
            # Other fields can be extracted from CSV or asked conversationally

        # GENERAL_QUERY doesn't require missing fields - we can answer without them

        return missing
