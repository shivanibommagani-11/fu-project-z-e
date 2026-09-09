"""
Tool for modifying contract execution dates using CONTRACT_NBR and AMMENDMENT_NBR.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.tools.base import BaseTool, ToolOutput
from app.database.models import Contract
from app.database.session import SessionLocal

logger = logging.getLogger(__name__)


class ExecutionDateTool(BaseTool):
    """Tool for updating contract execution dates matching Java NetSites logic."""

    name = "ExecutionDateTool"
    description = "Update execution date for a contract using contract_nbr and ammendment_nbr."

    def execute(
        self,
        contract_nbr: Optional[int] = None,
        ammendment_nbr: Optional[int] = 0,
        execution_date: Optional[str] = None,
        **kwargs
    ) -> ToolOutput:
        """
        Execute execution date modification matching Java NetSites endpoint behavior.
        """
        db: Session = SessionLocal()

        try:
            if contract_nbr is None:
                return ToolOutput(
                    success=False,
                    message="CONTRACT_NBR is required",
                    data={"missing_field": "contract_nbr", "field": "contract_nbr"},
                )

            if not execution_date or not str(execution_date).strip():
                return ToolOutput(
                    success=False,
                    message="Execution date is required in DD-Mon-YYYY format (e.g., '31-Jan-2028')",
                    data={"missing_field": "execution_date", "field": "execution_date"},
                )

            amm_nbr = int(ammendment_nbr) if ammendment_nbr is not None else 0

            # Hardcoded to INTRANET.CONTRACT to avoid the phantom table issue
            sql_stmt = text("""
                UPDATE INTRANET.CONTRACT
                SET EXECUTION_DT = TO_DATE(:new_date || ' ' || NVL(TO_CHAR(EXECUTION_DT, 'HH24:MI:SS'), '00:00:00'), 'DD-MON-YYYY HH24:MI:SS')
                WHERE CONTRACT_NBR = :contract_nbr
                  AND AMMENDMENT_NBR = :ammendment_nbr
            """)

            result = db.execute(
                sql_stmt,
                {
                    "new_date": str(execution_date).strip(),
                    "contract_nbr": int(contract_nbr),
                    "ammendment_nbr": amm_nbr,
                },
            )
            db.commit()

            rows_updated = result.rowcount

            if rows_updated == 0:
                return ToolOutput(
                    success=False,
                    message=f"No contract found with CONTRACT_NBR {contract_nbr} and AMMENDMENT_NBR {amm_nbr}",
                    data={"contract_nbr": contract_nbr, "ammendment_nbr": amm_nbr},
                )

            return ToolOutput(
                success=True,
                message=f"Successfully updated execution date for Contract #{contract_nbr}-{amm_nbr}",
                data={
                    "contract_nbr": int(contract_nbr),
                    "ammendment_nbr": amm_nbr,
                    "amendment_nbr": amm_nbr,
                    "new_execution_date": str(execution_date).strip(),
                    "rows_updated": rows_updated,
                },
            )

        except Exception as e:
            logger.error(f"Error updating execution date: {str(e)}", exc_info=True)
            db.rollback()
            return ToolOutput(
                success=False,
                message=f"Error updating execution date: {str(e)}",
                data={"error_type": type(e).__name__},
            )

        finally:
            db.close()