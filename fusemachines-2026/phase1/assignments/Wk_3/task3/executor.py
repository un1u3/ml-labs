from db import get_db
from sqlalchemy import text
from validator import validator
from logger import get_logger

logger = get_logger(__name__)


def executor(query: str):
    validator(query)

    db_gen = get_db()
    db = next(db_gen)

    try:
        result = db.execute(text(query))
        rows = result.fetchall()
        columns = result.keys()
        data = [dict(zip(columns, row)) for row in rows]
        return {'data': data, 'status': 'success'}
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return {'data': [], 'status': 'error', 'error': str(e)}
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass
