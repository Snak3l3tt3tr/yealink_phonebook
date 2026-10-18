"""
Main FastAPI application for the phonebook service.
"""
from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from typing import List, Literal
import uvicorn
import os
import csv
import io
from pydantic import ValidationError

from database import get_db, init_db
from models import Contact
from schemas import ContactCreate, ContactResponse, ContactUpdate, ImportSummary

app = FastAPI(title="Phonebook API", version="1.0.0")

# CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    init_db()


@app.get("/api")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Phonebook API is running"}


@app.get("/api/contacts", response_model=List[ContactResponse])
async def get_contacts(db: Session = Depends(get_db)):
    """Get all contacts."""
    contacts = db.query(Contact).all()
    return contacts


@app.get("/api/contacts/export.csv")
async def export_contacts(db: Session = Depends(get_db)):
    """Export every contact in a CSV format that can be imported again."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["name", "phone1", "phone2", "phone3"])

    for contact in db.query(Contact).order_by(Contact.id).all():
        writer.writerow(
            [
                contact.name,
                contact.phone1 or "",
                contact.phone2 or "",
                contact.phone3 or "",
            ]
        )

    return Response(
        # A UTF-8 BOM lets Windows Excel detect non-ASCII names correctly.
        content="\ufeff" + output.getvalue(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="phonebook-contacts.csv"'
        },
    )


@app.post("/api/contacts/import", response_model=ImportSummary)
async def import_contacts(
    file: UploadFile = File(...),
    duplicate_strategy: Literal["skip", "update", "error"] = Query("skip"),
    db: Session = Depends(get_db),
):
    """Import contacts from UTF-8 CSV and report problems per source row."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a .csv file")

    raw_content = await file.read(2 * 1024 * 1024 + 1)
    if len(raw_content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="CSV file must be 2 MB or smaller")

    try:
        csv_text = raw_content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV file must use UTF-8 encoding") from exc

    reader = csv.DictReader(io.StringIO(csv_text, newline=""))
    if reader.fieldnames is None:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    normalized_headers = [header.strip().lower() for header in reader.fieldnames]
    if len(normalized_headers) != len(set(normalized_headers)):
        raise HTTPException(status_code=400, detail="CSV contains duplicate column names")
    if "name" not in normalized_headers:
        raise HTTPException(status_code=400, detail="CSV must contain a 'name' column")

    allowed_headers = {"name", "phone1", "phone2", "phone3"}
    unknown_headers = sorted(set(normalized_headers) - allowed_headers)
    if unknown_headers:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported CSV columns: {', '.join(unknown_headers)}",
        )

    existing_by_name = {
        contact.name.strip().casefold(): contact
        for contact in db.query(Contact).order_by(Contact.id).all()
    }
    summary = {
        "total_rows": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "error_count": 0,
        "errors": [],
    }

    for row_number, source_row in enumerate(reader, start=2):
        if None in source_row:
            summary["total_rows"] += 1
            summary["errors"].append(
                {
                    "row": row_number,
                    "name": source_row.get("name"),
                    "message": "Row has more values than the CSV header",
                }
            )
            continue

        row = {
            header.strip().lower(): (value or "").strip()
            for header, value in source_row.items()
        }
        if not any(row.values()):
            continue

        summary["total_rows"] += 1
        contact_data = {
            "name": row.get("name", ""),
            "phone1": row.get("phone1") or None,
            "phone2": row.get("phone2") or None,
            "phone3": row.get("phone3") or None,
        }

        try:
            validated = ContactCreate.model_validate(contact_data)
        except ValidationError as exc:
            messages = []
            for error in exc.errors():
                field = ".".join(str(part) for part in error["loc"])
                messages.append(f"{field}: {error['msg']}")
            summary["errors"].append(
                {
                    "row": row_number,
                    "name": contact_data["name"] or None,
                    "message": "; ".join(messages),
                }
            )
            continue

        duplicate = existing_by_name.get(validated.name.casefold())
        if duplicate:
            if duplicate_strategy == "skip":
                summary["skipped"] += 1
                continue
            if duplicate_strategy == "error":
                summary["errors"].append(
                    {
                        "row": row_number,
                        "name": validated.name,
                        "message": "Duplicate contact name",
                    }
                )
                continue

            for field, value in validated.model_dump().items():
                if field in normalized_headers:
                    setattr(duplicate, field, value)
            summary["updated"] += 1
            continue

        contact = Contact(**validated.model_dump())
        db.add(contact)
        existing_by_name[validated.name.casefold()] = contact
        summary["created"] += 1

    summary["error_count"] = len(summary["errors"])
    db.commit()
    return summary


@app.get("/api/contacts/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """Get a specific contact by ID."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


@app.post("/api/contacts", response_model=ContactResponse, status_code=201)
async def create_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    """Create a new contact."""
    db_contact = Contact(**contact.model_dump())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact


@app.put("/api/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: int, contact: ContactUpdate, db: Session = Depends(get_db)
):
    """Update an existing contact."""
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    for key, value in contact.model_dump(exclude_unset=True).items():
        setattr(db_contact, key, value)

    db.commit()
    db.refresh(db_contact)
    return db_contact


@app.delete("/api/contacts/{contact_id}", status_code=204)
async def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    """Delete a contact."""
    db_contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not db_contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    db.delete(db_contact)
    db.commit()
    return Response(status_code=204)


@app.get("/yealink/phonebook.xml")
async def get_yealink_phonebook(db: Session = Depends(get_db)):
    """Generate the local-contact XML format exported by Yealink phones."""
    contacts = db.query(Contact).all()

    xml_lines = [
        '<?xml version="1.0" encoding="utf-8"?>',
        '<root_group>',
        '\t<group display_name="All Contacts" />',
        '\t<group display_name="Blacklist" />',
        '\t<group display_name="Blocklist" ring="" />',
        '</root_group>',
        '<root_contact>',
    ]

    for contact in contacts:
        xml_lines.append(
            '\t<contact '
            f'display_name="{_escape_xml(contact.name)}" '
            f'office_number="{_escape_xml(contact.phone1)}" '
            f'mobile_number="{_escape_xml(contact.phone2)}" '
            f'other_number="{_escape_xml(contact.phone3)}" '
            'line="-1" ring="Auto" group_id_name="All Contacts" />'
        )

    xml_lines.append('</root_contact>')

    xml_content = '\n'.join(xml_lines)
    return Response(
        content=xml_content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": 'attachment; filename="contact.xml"'},
    )


def _escape_xml(text: str) -> str:
    """Escape special XML characters."""
    if not text:
        return ""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;"))


# Mount static files for frontend (must be last to not override API routes)
frontend_dir = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
