from fastapi import FastAPI

from logger import get_logger
from router import router

logger = get_logger(__name__)

app = FastAPI(title="Concurrent Counts API")
app.include_router(router)

logger.info("Concurrent Counts API started")
