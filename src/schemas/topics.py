from pydantic import BaseModel


class TopicCreate(BaseModel):
    name: str
    room_id: int

class TopicUpdate(BaseModel):
    name: str
    room_id: int

class TopicResponse(BaseModel):
    id: int
    name: str
    room_id: int

    class Config:
        orm_mode = True

