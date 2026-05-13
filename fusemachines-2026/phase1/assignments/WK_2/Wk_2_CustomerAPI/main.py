from fastapi import FastAPI
from router import router
from logger import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Customer API")

app.include_router(router, prefix="/customers", tags=["customers"])

logger.info("Customer API started")