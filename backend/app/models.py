from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum as SQLEnum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from .database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    MANAGER = "manager"
    FINANCE = "finance"
    VIEWER = "viewer"

class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    file_path = Column(String, nullable=False)
    document_type = Column(String)                    # "invoice" or "credit_note"
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.PENDING)
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    uploaded_at = Column(DateTime, server_default=func.now())
    
    extracted_data = Column(JSON)                     # AI extracted fields
    duplicate = Column(Boolean, default=False)
    
    approvals = relationship("ApprovalStep", back_populates="document", cascade="all, delete-orphan")

class ApprovalStep(Base):
    __tablename__ = "approval_steps"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"))
    step_number = Column(Integer)                     # 1, 2, or 3
    role = Column(SQLEnum(UserRole))
    status = Column(String, default="pending")        # pending / approved / rejected
    approved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    comment = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=True)
    
    document = relationship("Document", back_populates="approvals")