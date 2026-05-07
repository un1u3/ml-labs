from fastapi import FastAPI
from pydantic import BaseModel 

app = FastAPI()




# this is all sync way 
@app.get('/')
def home():
    return {"msg":"My first fast API End point "}



@app.get('/users')
def get_users():
    return {"msg":['ram','shyam']}


@app.post('/userscreate')
def get_users():
    return {"msg":['ram','shyam']}

# now async method 


@app.get('/sync-users')
async def get_sync_users():
    return {'async users':['a','e']}


# path  parameters 

@app.get("/user/{user_id}")
async def get_user(user_id: int):
    return {'mgs':f"hello from user {user_id}  "}


# query param 

@app.get("/search")
async def search_item(q : str = None):
    return {'msg':f"found {q}" }


    # with pydantic 

class User(BaseModel):
    name : str
    age : int 
    is_active : bool


class UserOut(BaseModel):
    name: str
    age: int


@app.post('/users-pydantic', response_model = UserOut)
async def create_user(user: User):
    return {'data':user}
