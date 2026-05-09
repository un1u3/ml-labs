from pydantic import BaseModel, PostiveInt 



class User(BaseModel):
    id: int
    name : str
    