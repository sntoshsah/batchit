from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base
from models.associations import room_user_association

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

    rooms = relationship(
        "Room",
        secondary=room_user_association,
        back_populates="members",
        lazy="selectin",
    )

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
