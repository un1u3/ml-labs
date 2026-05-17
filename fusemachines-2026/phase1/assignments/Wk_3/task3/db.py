from dotenv import load_dotenv 
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os 
from logger import get_logger

load_dotenv()
logger = get_logger(__name__)

# read database url from .env 
DATABASE_URL = os.getenv("DATABASE_URL")
logger.info("Database connected successfully")


# create enginerr the actual connection 
engine = create_engine(DATABASE_URL)

# create session factory 
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# create base class for mdoels 

Base = declarative_base()
# func to ger a session 

def get_db():
    # openign a session
    db = SessionLocal()
    try:
        # waits until operation
        yield db 
    finally:
        db.close()
        logger.info("Database session closed")


