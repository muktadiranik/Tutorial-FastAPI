from pydantic import BaseModel
from typing import Optional
import random
from fastapi import FastAPI, HTTPException, status

app = FastAPI()

notes = [
    {
        "id": 1,
        "term": "variables",
        "definition": "A container for a value that can be changed",
        "learned": True,
        "tags": ["python"]
    },
    {
        "id": 2,
        "term": "functions",
        "definition": "A block of code that can be called to perform a specific task",
        "learned": True,
        "tags": ["python"]
    },
    {
        "id": 3,
        "term": "classes",
        "definition": "A blueprint for creating objects",
        "learned": True,
        "tags": ["python"]
    },
    {
        "id": 4,
        "term": "objects",
        "definition": "An instance of a class",
        "learned": True,
        "tags": ["python"]
    },
    {
        "id": 5,
        "term": "inheritance",
        "definition": "A way to create a new class that inherits the properties and methods of an existing class",
        "learned": True,
        "tags": ["python"]
    },
    {
        "id": 6,
        "term": "polymorphism",
        "definition": "A way to create a new class that can be used in place of an existing class",
        "learned": True,
        "tags": ["python"]
    }
]


class NoteRequest(BaseModel):
    term: Optional[str]
    definition: Optional[str]
    learned: bool
    tags: Optional[list[str]]


@app.get("/")
def home():
    return {"message": "Hello, FastAPI!"}


@app.get("/notes/random")
def get_random_note():
    if len(notes) == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="No notes found")
    return random.choice(notes)


@app.get("/notes")
def get_notes(tag: str | None = None, query: str | None = None):
    result = []
    for note in notes:
        if tag and tag not in note["tags"]:
            continue
        if query and query.lower() not in note["term"].lower():
            continue
        result.append(note)
    return result


@app.get("/notes/{note_id}")
def get_note(note_id: int):
    for note in notes:
        if note["id"] == note_id:
            return note
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail="Note not found")


@app.post("/notes")
def create_note(note: NoteRequest):
    for existing in notes:
        if existing["term"].lower() == note.term.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Term already exists")
    new_id = 1
    for existing in notes:
        new_id = existing["id"] + 1
    new_note = {
        "id": new_id,
    }
    new_note.update(note.model_dump())
    notes.append(new_note)
    return new_note


@app.patch("/notes/{note_id}")
def update_note(note_id: int, note: NoteRequest):
    for stored_note in notes:
        if stored_note["id"] == note_id:
            stored_note.update(note.model_dump(exclude_unset=True))
            return note
    return {"message": "Note not found"}


@app.delete("/notes/{note_id}")
def delete_note(note_id: int):
    for note in notes:
        if note["id"] == note_id:
            notes.remove(note)
            return {"message": "Note deleted"}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                        detail="Note not found")


@app.get("/statictics")
def get_statistics():
    learned = 0
    by_tag = {}

    for note in notes:
        if note["learned"]:
            learned += 1
        for tag in note["tags"]:
            by_tag[tag] = by_tag.get(tag, 0) + 1
    return {"total": len(notes), "learned": learned, "by_tag": by_tag}
