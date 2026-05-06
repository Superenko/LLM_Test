from pydantic import BaseModel


class BookBase(BaseModel):
    title: str
    author: str
    description: str
    year: int
    pages: int
    cover_url: str | None = None  # Новое поле


class BookCreate(BookBase):
    pass


class Book(BookBase):
    id: int

    class Config:
        from_attributes = True
