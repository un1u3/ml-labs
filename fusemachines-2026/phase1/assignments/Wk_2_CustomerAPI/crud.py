from sqlalchemy.orm import Session
from models import Customer
from schemas import CustomerCreate, CustomerUpdate
from logger import get_logger

logger = get_logger(__name__)


def get_customers(db: Session):
    logger.info("Fetching all customers")
    return db.query(Customer).all()


def get_customer(db: Session, customer_number: int):
    logger.info(f"Fetching customer {customer_number}")
    return db.query(Customer).filter(
        Customer.customerNumber == customer_number
    ).first()


def create_customer(db: Session, customer: CustomerCreate):
    logger.info(f"Creating customer {customer.customerName}")
    db_customer = Customer(**customer.model_dump())
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)
    return db_customer


def update_customer(db: Session, customer_number: int, customer: CustomerUpdate):
    logger.info(f"Updating customer {customer_number}")
    db_customer = get_customer(db, customer_number)

    if not db_customer:
        return None

    for key, value in customer.model_dump(exclude_unset=True).items():
        setattr(db_customer, key, value)

    db.commit()
    db.refresh(db_customer)
    return db_customer


def delete_customer(db: Session, customer_number: int):
    logger.info(f"Deleting customer {customer_number}")
    db_customer = get_customer(db, customer_number)

    if not db_customer:
        return None

    db.delete(db_customer)
    db.commit()
    return db_customer