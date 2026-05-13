from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from logger import get_logger
import crud
import schemas

router = APIRouter()
logger = get_logger(__name__)


@router.get("/", response_model=List[schemas.CustomerOut])
def list_customers(db: Session = Depends(get_db)):
    logger.info("GET /customers")
    return crud.get_customers(db)


@router.get("/{customer_number}", response_model=schemas.CustomerOut)
def get_customer(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"GET /customers/{customer_number}")
    customer = crud.get_customer(db, customer_number)

    if not customer:
        logger.warning(f"Customer not found: {customer_number}")
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer


@router.post("/", response_model=schemas.CustomerOut)
def create_customer(customer: schemas.CustomerCreate, db: Session = Depends(get_db)):
    logger.info("POST /customers")
    return crud.create_customer(db, customer)


@router.put("/{customer_number}", response_model=schemas.CustomerOut)
def update_customer(customer_number: int, customer: schemas.CustomerUpdate, db: Session = Depends(get_db)):
    logger.info(f"PUT /customers/{customer_number}")
    updated = crud.update_customer(db, customer_number, customer)

    if not updated:
        logger.warning(f"Customer not found: {customer_number}")
        raise HTTPException(status_code=404, detail="Customer not found")

    return updated


@router.delete("/{customer_number}", response_model=schemas.CustomerOut)
def delete_customer(customer_number: int, db: Session = Depends(get_db)):
    logger.info(f"DELETE /customers/{customer_number}")
    deleted = crud.delete_customer(db, customer_number)

    if not deleted:
        logger.warning(f"Customer not found: {customer_number}")
        raise HTTPException(status_code=404, detail="Customer not found")

    return deleted