from database import Base
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
import uuid
from models.associations import room_user_association

class Room(Base):
    __tablename__ = 'rooms'

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), unique=True, index=True, nullable=False)
    capacity = Column(Integer, nullable=True)
    
    # Many-to-Many with User
    members = relationship(
        "User",
        secondary=room_user_association,
        back_populates="rooms",
        lazy="selectin",
    )

    # One-to-Many with Knowledge
    knowledge_files = relationship(
        "Knowledge",
        back_populates="room",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<Room(name='{self.name}', capacity={self.capacity})>"


