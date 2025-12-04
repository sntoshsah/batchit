from database import get_db
from models import User, Room
from sqlalchemy.orm import Session
from fastapi import Depends


def list_room(db:Session=Depends(get_db)):
    rooms = db.query(Room).all()