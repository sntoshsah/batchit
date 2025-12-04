from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class Knowledge(Base):
    __tablename__ = 'knowledge'

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, index=True, nullable=False)
    filesize_kb = Column(Integer, nullable=False)
    filepath = Column(String(512), unique=True, index=True, nullable=False)
    room_id = Column(String(36), ForeignKey('rooms.id'), nullable=False)

    # Relationship back to Room (ONE-to-MANY)
    room = relationship("Room", back_populates="knowledge_files", lazy="selectin")

    def __repr__(self):
        return f"<Knowledge(filename='{self.filename}', filesize_kb={self.filesize_kb}, filepath='{self.filepath}')>"
