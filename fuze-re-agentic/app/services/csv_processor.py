"""
CSV and XLSX file processing and validation service.
"""

import logging
import io
from typing import List, Dict, Any
import pandas as pd
from fastapi import UploadFile

from app.api.schemas import ContractTerminationRecord
from app.config.settings import settings

logger = logging.getLogger(__name__)


def _get_file_type(filename: str) -> str:
    """
    Detect file type from filename extension.

    Args:
        filename: Name of the uploaded file

    Returns:
        File type: 'excel' for .xlsx, 'csv' for .csv

    Raises:
        ValueError: If file type is not supported
    """
    filename_lower = filename.lower()

    if filename_lower.endswith(('.xlsx', '.xls')):
        return 'excel'
    elif filename_lower.endswith('.csv'):
        return 'csv'
    else:
        raise ValueError(
            f"Unsupported file format: {filename}. "
            f"Please upload a CSV (.csv) or Excel (.xlsx) file."
        )


class CSVProcessor:
    """Service for processing and validating CSV files."""

    REQUIRED_COLUMNS = [
        "contract_nbr",
        "ammendment_nbr",
        "contract_said",
        "termination_dt",
        "termination_code",
        "description",
        "fas13_doc_id",
    ]

    @staticmethod
    async def process_upload_file(file: UploadFile) -> List[Dict[str, Any]]:
        """
        Process uploaded CSV or Excel file and return records as dicts.

        Args:
            file: Uploaded file from FastAPI (.csv or .xlsx)

        Returns:
            List of dictionaries representing file rows

        Raises:
            ValueError: If file is invalid, unsupported, or exceeds size limits
        """
        try:
            # Detect file type
            file_type = _get_file_type(file.filename)

            # Check file size
            content = await file.read()
            if len(content) > settings.csv_max_file_size:
                raise ValueError(
                    f"File size exceeds limit of {settings.csv_max_file_size / (1024*1024):.1f} MB"
                )

            # Read file based on type
            if file_type == 'excel':
                logger.info(f"Processing Excel file: {file.filename}")
                df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
            else:  # csv
                logger.info(f"Processing CSV file: {file.filename}")
                df = pd.read_csv(io.BytesIO(content))

            logger.info(f"Loaded {file_type} with {len(df)} rows and {len(df.columns)} columns")

            # Check row count
            if len(df) > settings.csv_max_rows:
                raise ValueError(
                    f"File contains {len(df)} rows, exceeds limit of {settings.csv_max_rows}"
                )

            # Convert to list of dicts
            records = df.to_dict("records")

            return records

        except pd.errors.EmptyDataError:
            raise ValueError("File is empty")
        except pd.errors.ParserError as e:
            raise ValueError(f"Invalid file format: {str(e)}")
        except ValueError as e:
            # Re-raise ValueError with our messages
            raise e
        except Exception as e:
            logger.error(f"Error processing file {file.filename}: {str(e)}", exc_info=True)
            raise ValueError(f"Error processing file: {str(e)}")

    @staticmethod
    def parse_csv_content(content: str) -> List[Dict[str, Any]]:
        """
        Parse CSV content from string.

        Args:
            content: CSV content as string

        Returns:
            List of dictionaries representing CSV rows
        """
        try:
            df = pd.read_csv(io.StringIO(content))

            logger.info(f"Parsed CSV with {len(df)} rows")

            # Check row count
            if len(df) > settings.csv_max_rows:
                raise ValueError(
                    f"CSV contains {len(df)} rows, exceeds limit of {settings.csv_max_rows}"
                )

            # Convert to list of dicts
            records = df.to_dict("records")

            return records

        except pd.errors.EmptyDataError:
            raise ValueError("CSV content is empty")
        except pd.errors.ParserError as e:
            raise ValueError(f"Invalid CSV format: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing CSV: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def validate_csv_structure(records: List[Dict[str, Any]]) -> None:
        """
        Validate that CSV has required columns.

        Args:
            records: List of CSV records

        Raises:
            ValueError: If required columns are missing
        """
        if not records:
            raise ValueError("CSV is empty")

        first_record = records[0]

        # Check for required columns (case-insensitive)
        record_keys = set(k.lower() for k in first_record.keys())

        missing_columns = []
        for required_col in CSVProcessor.REQUIRED_COLUMNS:
            if required_col.lower() not in record_keys:
                missing_columns.append(required_col)

        if missing_columns:
            raise ValueError(
                f"CSV missing required columns: {', '.join(missing_columns)}. "
                f"Required: {', '.join(CSVProcessor.REQUIRED_COLUMNS)}"
            )

    @staticmethod
    def normalize_headers(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalize CSV headers to lowercase and handle NaN values.

        Args:
            records: List of CSV records with potentially mixed-case headers

        Returns:
            List with normalized headers and cleaned NaN values
        """
        import pandas as pd
        normalized = []

        for record in records:
            # Normalize keys to lowercase and handle NaN values
            normalized_record = {}
            for k, v in record.items():
                # Convert NaN to None for easier handling
                if pd.isna(v):
                    normalized_record[k.lower()] = None
                else:
                    normalized_record[k.lower()] = v
            normalized.append(normalized_record)

        return normalized

    @staticmethod
    async def process_bulk_termination_csv(file: UploadFile) -> List[Dict[str, Any]]:
        """
        Process CSV file for bulk termination.

        Args:
            file: Uploaded CSV file

        Returns:
            List of validated contract termination records

        Raises:
            ValueError: If CSV is invalid
        """
        # Read file
        records = await CSVProcessor.process_upload_file(file)

        # Normalize headers
        records = CSVProcessor.normalize_headers(records)

        # Validate structure
        CSVProcessor.validate_csv_structure(records)

        logger.info(f"Successfully processed bulk termination CSV with {len(records)} records")

        return records
