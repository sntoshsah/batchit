from fastapi import APIRouter, Depends, HTTPException, Request
from requests import Session
from database import get_db
from models import Room, room_user_association,User
from schemas.room import RoomCreate, RoomUpdate, RoomResponse
import logging

logger = logging.getLogger(__name__)

room_router = APIRouter()


@room_router.get("/rooms/", response_model=list[RoomResponse])
async def list_rooms(request: Request, db=Depends(get_db)):
    rooms = db.query(Room).all()
    return rooms

@room_router.get("/rooms/{room_id}", response_model=RoomResponse)
async def get_room(room_id: str, request: Request, db=Depends(get_db)):
    db_room = db.query(Room).filter(Room.id == room_id).first()
    if not db_room:
        raise HTTPException(status_code=404, detail="Room not found")
    return db_room



# @room_router.post("/create_room/{room_name}")
# async def create_room(room_name: str, db: Session = Depends(get_db)):
#     rooms = db.query(Room).filter(Room.name == room_name).first()
#     if rooms:
#         return {"error": "Room already exists"}
#     user_id = Session.get("user_id")
#     if not user_id:
#         return {"error": "User not logged in"}
    
#     room_user = db.query(room_user_association).filter_by(user_id=user_id, room_id=rooms.id).first()
    
#     new_room = Room(name=room_name)
#     db.add(new_room)
#     db.commit()
#     db.refresh(new_room)
#     return {"message": f"Room '{room_name}' created"}


@room_router.post("/create_room/{room_name}")
async def create_room(
    request: Request,
    room_name: str,
    db: Session = Depends(get_db)
):
    # 1. Check if room already exists
    existing_room = db.query(Room).filter(Room.name == room_name).first()
    if existing_room:
        return {"error": "Room already exists"}

    # 2. Check logged-in user from session
    user_id = request.session.get("user_id")
    if not user_id:
        logger.warning("No user_id found in session")
        return {"error": "User not logged in"}

    # 3. Fetch the logged-in user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        logger.error(f"User with id {user_id} not found in database")
        return {"error": "Invalid user"}

    # 4. Create new room
    new_room = Room(name=room_name)

    # 5. Add creator to the room (auto inserts into room_user table)
    new_room.members.append(user)

    # 6. Save to database
    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return {"message": f"Room '{room_name}' created successfully", "room_id": new_room.id}
