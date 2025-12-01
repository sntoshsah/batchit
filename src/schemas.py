from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class GroupCreate(BaseModel):
    name: str

class TopicCreate(BaseModel):
    name: str
    group_id: int

class MessageCreate(BaseModel):
    topic_id: int
    user_id: int
    content: str

class DocumentCreate(BaseModel):
    topic_id: int
    user_id: int
    title: str
    content: str

class DocumentUpdate(BaseModel):
    title: str
    content: str
