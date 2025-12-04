from fastapi import APIRouter, Depends, HTTPException, Request
from requests import Session
from database import get_db
from models import Room
from schemas.room import RoomCreate, RoomUpdate, RoomResponse

room_router = APIRouter()

# @room_router.post("/rooms/")
# async def create_room(room: RoomCreate, request: Request, db=Depends(get_db)):
#     rooms = db.query(Room).filter(Room.name == room.name).first()
#     if rooms:
#         raise HTTPException(status_code=400, detail="Room with this name already exists")
#     db_room = Room(name=room.name, capacity=room.capacity)
#     db.add(db_room)
#     db.commit()
#     db.refresh(db_room)
#     return db_room

@room_router.get("/rooms/", response_model=list[RoomResponse])
async def list_rooms(request: Request, db=Depends(get_db)):
    rooms = db.query(Room).all()
    print(rooms)
    return rooms

@room_router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room(room_id: str, request: Request, db=Depends(get_db)):
    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    return db_room



@room_router.post("/create_room/{room_name}")
async def create_room(room_name: str, db: Session = Depends(get_db)):
    rooms = db.query(Room).filter(Room.name == room_name).first()
    if rooms:
        return {"error": "Room already exists"}
    new_room = Room(name=room_name)
    db.add(new_room)
    db.commit()
    db.refresh(new_room)
    return {"message": f"Room '{room_name}' created"}
