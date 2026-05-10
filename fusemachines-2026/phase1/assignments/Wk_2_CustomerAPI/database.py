from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

load_dotenv()
logger = get_logger(__name__) 
# 1. read the URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")
logger.info("Database connected successfully")

# 2. create engine (the actual connection)
engine = create_engine(DATABASE_URL)

# 3. create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. create base class for models
Base = declarative_base()

# 5. function to get a session
def get_db():
    # OPening a session
    db = SessionLocal()    
    try:
        # waits until operations
        yield db
    finally:
        # closes
        db.close()
        logger.info("Database session closed")

        
