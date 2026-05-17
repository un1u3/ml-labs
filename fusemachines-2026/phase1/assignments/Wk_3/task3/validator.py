# blocks delete operations by LLM
from logger import get_logger
logger = get_logger(__name__)

def validator(query: str):
    block = ['DELETE','DROP',"CREATE","ALTER","INSERT"]
    query_upper = query.strip().upper()
    for keyword in block:
        if keyword in query_upper:
            raise ValueError(f"Blocked query: {keyword} not allowed")