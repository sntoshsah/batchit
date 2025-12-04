from pydantic import BaseModel

class DocumentCreate(BaseModel):
    file_name: str
    file_path: str
    file_size: int
    room_id: int
    user_id: int
    
    
    class Config:
        from_attributes = True
