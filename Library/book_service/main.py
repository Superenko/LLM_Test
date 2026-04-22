from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import models, schemas, crud
from .database import SessionLocal, engine, Base
import os
from typing import List
from PyPDF2 import PdfReader

app = FastAPI()

# Create tables
Base.metadata.create_all(bind=engine)

def seed_books(db):
    if not db.query(models.Book).first():
        books = [
            models.Book(
                title="1984",
                author="Джордж Оруэлл",
                description="Антиутопия о тоталитарном будущем.",
                year=1949,
                pages=328,
                cover_url="https://covers.openlibrary.org/b/id/7222246-L.jpg"
            ),
            models.Book(
                title="Мастер и Маргарита",
                author="Михаил Булгаков",
                description="Мистический роман о добре и зле.",
                year=1967,
                pages=480,
                cover_url="https://covers.openlibrary.org/b/id/8231856-L.jpg"
            )
        ]
        db.add_all(books)
        db.commit()

with SessionLocal() as db:
    seed_books(db)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/books", response_model=schemas.Book)
def create_book(book: schemas.BookCreate, db: Session = Depends(get_db)):
    return crud.create_book(db, book)

@app.get("/books", response_model=list[schemas.Book])
def read_books(db: Session = Depends(get_db)):
    return crud.get_books(db)

@app.get("/books/{book_id}", response_model=schemas.Book)
def read_book(book_id: int, db: Session = Depends(get_db)):
    db_book = crud.get_book(db, book_id)
    if db_book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return db_book

@app.put("/books/{book_id}", response_model=schemas.Book)
def update_book(book_id: int, book: schemas.BookCreate, db: Session = Depends(get_db)):
    updated = crud.update_book(db, book_id, book)
    if updated is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return updated

@app.delete("/books/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_book(db, book_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book deleted"}

@app.get("/debug/books")
def debug_books(db: Session = Depends(get_db)):
    books = db.query(models.Book).all()
    return [{"id": b.id, "title": b.title, "author": b.author, "year": b.year, "pages": b.pages} for b in books]

@app.post("/books/upload", response_model=schemas.Book)
def upload_book(
    title: str = Form(...),
    author: str = Form(...),
    genre: str = Form(...),
    description: str = Form(''),
    year: int = Form(...),
    cover_url: str = Form(''),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # Зберігаємо файл
    upload_dir = "uploaded_books"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as f:
        f.write(file.file.read())

    # Визначаємо кількість сторінок та контент
    pages = 0
    content: List[str] = []
    if file.filename.lower().endswith(".pdf"):
        reader = PdfReader(file_path)
        pages = len(reader.pages)
        for page in reader.pages:
            content.append(page.extract_text() or "")
    elif file.filename.lower().endswith(".txt"):
        with open(file_path, encoding="utf-8") as f:
            text = f.read()
        # Розбиваємо текст на сторінки по 1500 символів
        content = [text[i:i+1500] for i in range(0, len(text), 1500)]
        pages = len(content)
    else:
        raise HTTPException(400, "Підтримуються лише PDF та TXT")

    # Створюємо книгу
    book = schemas.BookCreate(
        title=title,
        author=author,
        description=description,
        year=year,
        pages=pages,
        cover_url=cover_url
    )
    db_book = crud.create_book(db, book)
    # Зберігаємо шлях до файлу та контент у окремій папці (можна додати у БД, якщо потрібно)
    content_dir = os.path.join(upload_dir, f"book_{db_book.id}")
    os.makedirs(content_dir, exist_ok=True)
    with open(os.path.join(content_dir, "content.txt"), "w", encoding="utf-8") as f:
        for page in content:
            f.write(page + "\n---PAGE_BREAK---\n")
    db_book.file_url = file_path
    db.commit()
    db.refresh(db_book)
    return db_book

@app.get("/books/{book_id}/content")
def get_book_content(book_id: int, db: Session = Depends(get_db)):
    upload_dir = "uploaded_books"
    content_dir = os.path.join(upload_dir, f"book_{book_id}")
    content_file = os.path.join(content_dir, "content.txt")
    if not os.path.exists(content_file):
        raise HTTPException(404, "Контент не знайдено")
    with open(content_file, encoding="utf-8") as f:
        raw = f.read()
    pages = [p.strip() for p in raw.split("---PAGE_BREAK---") if p.strip()]
    return {"pages": pages}
