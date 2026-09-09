"""
Database initialization and seeding with sample data.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from app.database.models import Contract, ContractPmtDate
from app.database.session import SessionLocal, init_db


def seed_contracts(db: Session):
    """Populate database with sample contract data for testing."""

    # Check if data already exists
    existing_count = db.query(Contract).count()
    if existing_count > 0:
        print(f"[OK] Database already seeded with {existing_count} contracts")
        return

    # Generate 100 sample contracts
    sample_contracts = []

    # Tenant names for variety
    tenant_names = [
        "Acme Corporation", "Tech Innovations Inc", "Global Services Ltd",
        "Enterprise Solutions", "Digital Dynamics", "Future Systems",
        "Alliance Partners", "Premier Industries", "Apex Group",
        "Zenith Companies", "Velocity Partners", "Catalyst Enterprises",
    ]

    statuses = ["ACTIVE", "ACTIVE", "ACTIVE", "TERMINATED", "PENDING"]

    # Generate contracts with SAID starting from 100000
    for i in range(100):
        contract_said = 100000 + i
        contract_nbr = 200000 + (i * 123) % 100000  # Generate unique contract numbers

        # Vary execution dates
        execution_year = 2015 + (i % 10)
        execution_month = (i % 12) + 1
        execution_day = min((i % 28) + 1, 28)

        # Vary commencement dates
        commencement_year = execution_year - (i % 3)
        commencement_month = ((i + 3) % 12) + 1

        # Vary expiration dates
        expiration_year = execution_year + 5 + (i % 5)

        # Vary rent amounts
        base_rent = Decimal(str(30000 + (i * 1234) % 80000))
        annual_rent = base_rent * 12
        square_footage = Decimal(str(10000 + (i * 345) % 40000))

        tenant_name = tenant_names[i % len(tenant_names)]
        status = statuses[i % len(statuses)]

        contract = Contract(
            contract_said=contract_said,
            contract_nbr=contract_nbr,
            ammendment_nbr=i % 3,
            execution_dt=datetime(execution_year, execution_month, execution_day).date(),
            commencement_dt=datetime(commencement_year, commencement_month, 1).date(),
            expiration_dt=datetime(expiration_year, 12, 31).date(),
            termination_dt=datetime(expiration_year, 12, 31).date() if status == "TERMINATED" else None,
            contract_status=status,
            is_active=(status == "ACTIVE"),
            contract_desc=f"Contract {i+1} - {tenant_name}",
            fas13_doc_id=f"DOC{i+1:03d}",
            tenant_name=tenant_name,
            base_rent=base_rent,
            annual_rent=annual_rent,
            square_footage=square_footage,
            gl_account=f"GL{(i % 50):02d}",
            cost_center=f"CC{(i % 30):02d}",
            lease_type="OPERATING" if i % 2 == 0 else "FINANCE",
            building_id=f"BLD{(i % 15):03d}",
            space_id=f"SP{(i % 50):03d}",
            tenant_id=f"TEN{(i % 20):03d}",
            affiliate_flag=1 if i % 5 == 0 else 0,
            affiliate_id=f"AFF{(i % 10):02d}" if i % 5 == 0 else None,
        )
        sample_contracts.append(contract)

    # Add all contracts
    for contract in sample_contracts:
        db.add(contract)

    db.commit()

    # Create payment date records
    payment_records = []
    for contract in sample_contracts:
        # Create quarterly payment records for each contract
        for quarter in range(1, 5):
            month = (quarter - 1) * 3 + 1
            payment_date = ContractPmtDate(
                contract_said=contract.contract_said,
                payment_start_dt=datetime(2024, month, 1).date(),
                payment_end_dt=datetime(2024, month + 2, 1).date(),
                payment_amount=contract.base_rent / 4,
                payment_frequency="QUARTERLY",
                prorate_termination_compl_ind=0,
                termination_processed_ind=0,
            )
            payment_records.append(payment_date)

    for payment in payment_records:
        db.add(payment)

    db.commit()
    print(f"[OK] Seeded {len(sample_contracts)} contracts with {len(payment_records)} payment records")


def main():
    """Initialize database with tables and sample data."""
    print("Initializing database...")

    # Create tables
    init_db()

    # Seed data
    db = SessionLocal()
    try:
        seed_contracts(db)
    finally:
        db.close()

    print("[OK] Database initialization complete!")


if __name__ == "__main__":
    main()
