from sql_generator import fix_sql, generate_sql, translate_to_nlp
from executor import executor
from logger import get_logger

# for fast 
from fastapi import FastAPI
from pydantic import BaseModel 

class QuestionRequest(BaseModel):
    question: str


logger = get_logger(__name__)


# for fast API

app = FastAPI()



@app.post('/')
def tex2sql(request: QuestionRequest):

    sql = generate_sql(request.question)

    logger.info(f"Generated SQL: {sql}")

    output = executor(sql)
   

    if output["status"] == "error":
        logger.info("First attempt failed, retrying...")
        sql = fix_sql(request.question, sql, output["error"])
        logger.info(f"Fixed SQL: {sql}")
        output = executor(sql)
    summary = translate_to_nlp(sql)
    print(f"output : {output['data']}")
    print(f'summary:{summary}')

    logger.info(f"Final status: {output['status']}")
    return {
        "sql": sql,
        "result": output["data"],
        "summary": summary,
        "status": output["status"]
    }
