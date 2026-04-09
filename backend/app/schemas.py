from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
from .models import UserRole, DocumentStatus

# Auth schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.VIEWER
    
    @field_validator('password')
    @classmethod
    def validate_password_length(cls, v):
        if len(v.encode('utf-8')) > 72:
            raise ValueError('Password must be 72 bytes or less (bcrypt limitation)')
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Document schemas
class DocumentCreate(BaseModel):
    document_type: str  # "invoice" or "credit_note"

class ExtractedData(BaseModel):
    vendor: Optional[str] = None
    invoice_number: Optional[str] = None
    date: Optional[str] = None
    amount: Optional[float] = None
    vat: Optional[float] = None

class DocumentResponse(BaseModel):
    id: int
    document_type: str
    status: DocumentStatus
    extracted_data: Optional[Dict[str, Any]] = None
    uploaded_at: datetime
    duplicate: bool
class ApprovalAction(BaseModel):
    document_id: int
    step_number: int
    action: str          # "approve" or "reject"
    comment: Optional[str] = None

class ApprovalResponse(BaseModel):
    document_id: int
    step_number: int
    status: str
    approved_by: int
    comment: Optional[str] = None
    
    class Config:
        from_attributes = True