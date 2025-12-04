from pydantic import BaseModel

class MessageCreate(BaseModel):
    content: str
    topic_id: int
    user_id: int

    class Config:
        from_attributes = True

class MessageRead(BaseModel):
    id: int
    content: str
    topic_id: int
    user_id: int

    class Config:
        from_attributes = True
