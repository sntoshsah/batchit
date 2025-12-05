from sqlalchemy import Table, Column, Integer, String, ForeignKey
from database import Base

room_user_association = Table(
    'room_user',
    Base.metadata,
    Column('room_id', String(36), ForeignKey('rooms.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
)

room_knowledge_association = Table(
    'room_knowledge',
    Base.metadata,
    Column('room_id', String(36), ForeignKey('rooms.id'), primary_key=True),
    Column('knowledge_id', String(36), ForeignKey('knowledge.id'), primary_key=True),
)

