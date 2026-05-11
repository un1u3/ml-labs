import asyncio
from time import perf_counter

from fastapi import APIRouter, HTTPException

import crud
from logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


async def get_count(name, count_function):
    logger.info("Incoming request: GET /%s/count", name)

    try:
        count = await count_function()
        logger.info("Success response: GET /%s/count", name)
        return {name: count}
    except Exception as exc:
        logger.exception("Failure response: GET /%s/count", name)
        raise HTTPException(status_code=500, detail=f"Could not count {name}") from exc


@router.get("/customers/count")
async def customers_count():
    return await get_count("customers", crud.count_customers)


@router.get("/orders/count")
async def orders_count():
    return await get_count("orders", crud.count_orders)


@router.get("/products/count")
async def products_count():
    return await get_count("products", crud.count_products)


@router.get("/employees/count")
async def employees_count():
    return await get_count("employees", crud.count_employees)


@router.get("/offices/count")
async def offices_count():
    return await get_count("offices", crud.count_offices)


@router.get("/payments/count")
async def payments_count():
    return await get_count("payments", crud.count_payments)


@router.get("/orderdetails/count")
async def orderdetails_count():
    return await get_count("orderdetails", crud.count_orderdetails)


@router.get("/productlines/count")
async def productlines_count():
    return await get_count("productlines", crud.count_productlines)


@router.get("/overall_counts")
async def overall_counts():
    logger.info("Incoming request: GET /overall_counts")
    start_time = perf_counter()

    names = [
        "customers",
        "orders",
        "products",
        "employees",
        "offices",
        "payments",
        "orderdetails",
        "productlines",
    ]

    tasks = [
        crud.count_customers(),
        crud.count_orders(),
        crud.count_products(),
        crud.count_employees(),
        crud.count_offices(),
        crud.count_payments(),
        crud.count_orderdetails(),
        crud.count_productlines(),
    ]

    try:
        logger.info("Starting all count tasks concurrently")
        counts = await asyncio.gather(*tasks)
        logger.info("asyncio.gather completed")

        response = dict(zip(names, counts))
        elapsed = perf_counter() - start_time
        logger.info("Success response: GET /overall_counts in %.4f seconds", elapsed)
        return response
    except Exception as exc:
        elapsed = perf_counter() - start_time
        logger.exception("Failure response: GET /overall_counts after %.4f seconds", elapsed)
        raise HTTPException(status_code=500, detail="Could not load overall counts") from exc
