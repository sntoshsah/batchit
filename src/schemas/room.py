from pydantic import BaseModel
import uuid

class RoomCreate(BaseModel):
    name: str
    capacity: int


class RoomUpdate(BaseModel):
    name: str | None = None
    capacity: int | None = None

class RoomResponse(BaseModel):
    id: int
    name: str
    capacity: int

    class Config:
        from_attributes = True

class RoomIDResponse(BaseModel):
    id: int

    class Config:
        from_attributes = True


