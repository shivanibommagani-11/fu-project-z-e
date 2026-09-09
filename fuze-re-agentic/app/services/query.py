"""
Query service for executing parameterized SQL operations.
"""

import logging
from typing import Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.database.models import Contract, ContractPmtDate
from app.database.session import SessionLocal

logger = logging.getLogger(__name__)


class QueryService:
    """Service for executing database queries with proper parameter handling."""

    @staticmethod
    def update_contract_execution_date(
        contract_said: int,
        contract_nbr: int,
        ammendment_nbr: int,
        execution_date: str,
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Update contract execution date with parameterized query.

        Args:
            contract_said: Contract System Assigned ID
            contract_nbr: Contract number
            ammendment_nbr: Amendment number
            execution_date: Date in DD-MON-YYYY format
            db: Database session

        Returns:
            Dict with update result details
        """
        if db is None:
            db = SessionLocal()

        try:
            # Parse date string (DD-MON-YYYY) to datetime object
            parsed_date = datetime.strptime(execution_date, "%d-%b-%Y").date()

            logger.info(
                f"Updating EXECUTION_DT for contract SAID {contract_said}: {parsed_date}"
            )

            # Parameterized query to prevent SQL injection
            stmt = (
                update(Contract)
                .where(
                    (Contract.contract_said == contract_said)
                    & (Contract.contract_nbr == contract_nbr)
                    & (Contract.ammendment_nbr == ammendment_nbr)
                )
                .values(execution_dt=parsed_date, last_modified_dt=datetime.utcnow())
            )

            result = db.execute(stmt)
            db.commit()

            return {
                "success": True,
                "rows_updated": result.rowcount,
                "contract_said": contract_said,
                "contract_nbr": contract_nbr,
                "ammendment_nbr": ammendment_nbr,
                "new_execution_date": execution_date,
            }

        except ValueError as e:
            logger.error(f"Date parsing error: {str(e)}")
            db.rollback()
            raise
        except Exception as e:
            logger.error(f"Database error: {str(e)}", exc_info=True)
            db.rollback()
            raise
        finally:
            if db:
                db.close()

    @staticmethod
    def bulk_terminate_contracts(
        contract_saids: List[int],
        termination_date: str,
        termination_code: str,
        description: str,
        fas13_doc_id: str = "NOREQ",
        db: Session = None,
    ) -> Dict[str, Any]:
        """
        Bulk terminate contracts with parameterized queries.

        Args:
            contract_saids: List of contract SAIDs to terminate
            termination_date: Termination date in DD-MON-YYYY format
            termination_code: Termination code
            description: Termination reason
            fas13_doc_id: FAS13 document ID
            db: Database session

        Returns:
            Dict with operation result details
        """
        if db is None:
            db = SessionLocal()

        try:
            if not contract_saids or len(contract_saids) == 0:
                raise ValueError("No contracts to terminate")

            # Parse date
            parsed_date = datetime.strptime(termination_date, "%d-%b-%Y").date()

            logger.info(
                f"Bulk terminating {len(contract_saids)} contracts with code {termination_code}"
            )

            # Update CONTRACT table with parameterized query
            stmt1 = (
                update(Contract)
                .where(Contract.contract_said.in_(contract_saids))
                .values(
                    termination_dt=parsed_date,
                    termination_code=termination_code,
                    contract_desc=description,
                    fas13_doc_id=fas13_doc_id,
                    last_modified_dt=datetime.utcnow(),
                )
            )

            result1 = db.execute(stmt1)
            rows_updated_contract = result1.rowcount

            logger.info(f"Updated {rows_updated_contract} CONTRACT records")

            # Update CONTRACT_PMT_DATE table
            stmt2 = (
                update(ContractPmtDate)
                .where(ContractPmtDate.contract_said.in_(contract_saids))
                .values(prorate_termination_compl_ind=0)
            )

            result2 = db.execute(stmt2)
            rows_updated_pmt = result2.rowcount

            logger.info(f"Updated {rows_updated_pmt} CONTRACT_PMT_DATE records")

            # Commit transaction
            db.commit()

            return {
                "success": True,
                "total_contracts": len(contract_saids),
                "contracts_updated": rows_updated_contract,
                "payment_dates_updated": rows_updated_pmt,
                "termination_date": termination_date,
                "termination_code": termination_code,
            }

        except ValueError as e:
            logger.error(f"Validation error: {str(e)}")
            db.rollback()
            raise
        except Exception as e:
            logger.error(f"Database error during bulk termination: {str(e)}", exc_info=True)
            db.rollback()
            raise
        finally:
            if db:
                db.close()

    @staticmethod
    def get_contract_by_said(contract_said: int, db: Session = None) -> Contract:
        """
        Get contract by SAID.

        Args:
            contract_said: Contract System Assigned ID
            db: Database session

        Returns:
            Contract object or None if not found
        """
        if db is None:
            db = SessionLocal()

        try:
            contract = db.query(Contract).filter(Contract.contract_said == contract_said).first()
            return contract
        finally:
            db.close()

    @staticmethod
    def get_contracts_by_nbr(contract_nbr: int, db: Session = None) -> List[Contract]:
        """
        Get all contracts by contract number.

        Args:
            contract_nbr: Contract number
            db: Database session

        Returns:
            List of Contract objects
        """
        if db is None:
            db = SessionLocal()

        try:
            contracts = (
                db.query(Contract)
                .filter(Contract.contract_nbr == contract_nbr)
                .order_by(Contract.ammendment_nbr.desc())
                .all()
            )
            return contracts
        finally:
            db.close()
