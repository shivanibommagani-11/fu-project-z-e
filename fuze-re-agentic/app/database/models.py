"""
SQLAlchemy ORM models for Fuze Real Estate database.
Mirrors the production INTRANET schema exactly.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, DateTime, Date,
    Numeric, Boolean, Text, TIMESTAMP, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, foreign

Base = declarative_base()


class Contract(Base):
    """CONTRACT table - Core contract records."""

    __tablename__ = "CONTRACT"
    __table_args__ = (
        UniqueConstraint("contract_said", name="uq_contract_contract_said"),
    )

    # Primary Keys
    contract_said = Column(Integer, primary_key=True, index=True)
    contract_nbr = Column(Integer, nullable=False, index=True)
    ammendment_nbr = Column(Integer, default=0, primary_key=True)

    # Key Dates
    execution_dt = Column(Date, nullable=True)
    termination_dt = Column(Date, nullable=True)
    creation_dt = Column(DateTime, default=datetime.utcnow)

    # Termination Info
    termination_code = Column(String(20), nullable=True)
    contract_desc = Column(Text, nullable=True)

    # Financial/Administrative Fields
    fas13_doc_id = Column(String(50), nullable=True)

    # Lease/Space Details
    lease_type = Column(String(50), nullable=True)
    building_id = Column(Integer, nullable=True)
    space_id = Column(Integer, nullable=True)

    # Tenant Information
    tenant_id = Column(Integer, nullable=True)
    tenant_name = Column(String(255), nullable=True)

    # Financial Details
    base_rent = Column(Numeric(15, 2), nullable=True)
    annual_rent = Column(Numeric(15, 2), nullable=True)
    square_footage = Column(Numeric(12, 2), nullable=True)

    # Service Dates
    commencement_dt = Column(Date, nullable=True)
    expiration_dt = Column(Date, nullable=True)
    option_expiration_dt = Column(Date, nullable=True)

    # Status Fields
    contract_status = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True)

    # Affiliate Information
    affiliate_flag = Column(String(1), nullable=True)
    affiliate_id = Column(Integer, nullable=True)

    # Additional Identifiers
    gl_account = Column(String(50), nullable=True)
    cost_center = Column(String(50), nullable=True)

    # Audit Fields
    last_modified_dt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(100), nullable=True)
    modified_by = Column(String(100), nullable=True)

    # Relationships
    payment_dates = relationship(
        "ContractPmtDate",
        back_populates="contract",
        primaryjoin="Contract.contract_said == foreign(ContractPmtDate.contract_said)",
    )

    def __repr__(self):
        return f"<Contract(said={self.contract_said}, nbr={self.contract_nbr}, amendment={self.ammendment_nbr})>"


class ContractPmtDate(Base):
    """CONTRACT_PMT_DATE table - Payment schedule and termination indicators."""

    __tablename__ = "CONTRACT_PMT_DATE"

    # Primary Keys
    contract_pmt_date_id = Column(Integer, primary_key=True, autoincrement=True)
    contract_said = Column(Integer, nullable=False, index=True)

    # Payment Information
    payment_start_dt = Column(Date, nullable=True)
    payment_end_dt = Column(Date, nullable=True)
    payment_amount = Column(Numeric(15, 2), nullable=True)
    payment_frequency = Column(String(30), nullable=True)

    # Termination Indicators
    prorate_termination_compl_ind = Column(Integer, default=0)
    termination_processed_ind = Column(Integer, default=0)

    # Audit Fields
    created_dt = Column(DateTime, default=datetime.utcnow)
    modified_dt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    contract = relationship(
        "Contract",
        back_populates="payment_dates",
        primaryjoin="foreign(ContractPmtDate.contract_said) == Contract.contract_said",
    )

    def __repr__(self):
        return f"<ContractPmtDate(id={self.contract_pmt_date_id}, contract_said={self.contract_said})>"


class ContractAudit(Base):
    """Audit log for contract modifications."""

    __tablename__ = "CONTRACT_AUDIT"

    audit_id = Column(Integer, primary_key=True, autoincrement=True)
    contract_said = Column(Integer, index=True, nullable=False)
    action_type = Column(String(50), nullable=False)  # INSERT, UPDATE, DELETE, etc.
    field_name = Column(String(100), nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    user_id = Column(String(100), nullable=True)
    action_dt = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<ContractAudit(id={self.audit_id}, contract_said={self.contract_said}, action={self.action_type})>"
