import asyncio

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from database import SessionLocal
from logger import get_logger

logger = get_logger(__name__)


def _count_table_sync(table_name):
    logger.info("Starting count query for %s", table_name)
    db = SessionLocal()

    try:
        result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
        count = result.scalar()
        safe_count = int(count or 0)
        logger.info("Completed count query for %s: %s", table_name, safe_count)
        return safe_count
    except SQLAlchemyError:
        logger.exception("Database error while counting %s", table_name)
        raise
    finally:
        db.close()

# async for concurrent operaatiosn, 
async def _count_table(table_name):
    return await asyncio.to_thread(_count_table_sync, table_name)


async def count_customers():
    return await _count_table("customers")


async def count_orders():
    return await _count_table("orders")


async def count_products():
    return await _count_table("products")


async def count_employees():
    return await _count_table("employees")


async def count_offices():
    return await _count_table("offices")


async def count_payments():
    return await _count_table("payments")


async def count_orderdetails():
    return await _count_table("orderdetails")


async def count_productlines():
    return await _count_table("productlines")
