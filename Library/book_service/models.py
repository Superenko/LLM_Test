from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    author = Column(String)
    description = Column(Text)
    year = Column(Integer)
    pages = Column(Integer)
    cover_url = Column(String, nullable=True)  # Новое поле для обложки
