"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import List, Optional


class ContactBase(BaseModel):
    """Base contact schema."""
    name: str = Field(..., min_length=1, max_length=255)
    phone1: Optional[str] = Field(None, max_length=50)
    phone2: Optional[str] = Field(None, max_length=50)
    phone3: Optional[str] = Field(None, max_length=50)


class ContactCreate(ContactBase):
    """Schema for creating a contact."""
    pass


class ContactUpdate(ContactBase):
    """Schema for updating a contact (all fields optional)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)


class ContactResponse(ContactBase):
    """Schema for contact response with ID."""
    id: int

    model_config = ConfigDict(from_attributes=True)


class ImportRowError(BaseModel):
    """A validation or duplicate error tied to a source CSV row."""

    row: int
    name: Optional[str] = None
    message: str


class ImportSummary(BaseModel):
    """Counts and row-level errors returned after a CSV import."""

    total_rows: int
    created: int
    updated: int
    skipped: int
    error_count: int
    errors: List[ImportRowError]


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def passwords_match(self):
        if self.new_password != self.confirm_password:
            raise ValueError("New passwords do not match")
        return self
