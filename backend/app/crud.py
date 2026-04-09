from sqlalchemy.orm import Session
from . import models, schemas, auth
from .database import SessionLocal
from fastapi import HTTPException
from datetime import datetime

def get_db_from_auth():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user or not auth.verify_password(password, user.hashed_password):
        return False
    return user

# ==================== Document CRUD ====================

def create_document(db: Session, file_path: str, document_type: str, extracted_data: dict, uploaded_by: int):
    db_document = models.Document(
        file_path=file_path,
        document_type=document_type,
        extracted_data=extracted_data,
        uploaded_by=uploaded_by
    )
    db.add(db_document)
    db.commit()
    db.refresh(db_document)
    
    # Create 3-step approval workflow
    for step in [1, 2, 3]:
        role = models.UserRole.REVIEWER if step == 1 else \
               models.UserRole.MANAGER if step == 2 else models.UserRole.FINANCE
        approval = models.ApprovalStep(
            document_id=db_document.id,
            step_number=step,
            role=role
        )
        db.add(approval)
    db.commit()
    
    return db_document

def get_document(db: Session, document_id: int):
    return db.query(models.Document).filter(models.Document.id == document_id).first()

def check_duplicate(db: Session, invoice_number: str = None, vendor: str = None, amount: float = None):
    if invoice_number:
        return db.query(models.Document).filter(
            models.Document.extracted_data["invoice_number"].astext == invoice_number
        ).first()
    return None

# ==================== Approval Workflow ====================

def get_next_approval_step(db: Session, document_id: int):
    """Get the current pending approval step for a document"""
    return db.query(models.ApprovalStep).filter(
        models.ApprovalStep.document_id == document_id,
        models.ApprovalStep.status == "pending"
    ).order_by(models.ApprovalStep.step_number).first()

def approve_document(
    db: Session, 
    document_id: int, 
    step_number: int, 
    user_id: int, 
    comment: str = None
):
    approval_step = db.query(models.ApprovalStep).filter(
        models.ApprovalStep.document_id == document_id,
        models.ApprovalStep.step_number == step_number
    ).first()

    if not approval_step:
        raise HTTPException(status_code=404, detail="Approval step not found")

    approval_step.status = "approved"
    approval_step.approved_by = user_id
    approval_step.comment = comment
    approval_step.timestamp = datetime.utcnow()

    # Check if all steps are approved
    all_approved = db.query(models.ApprovalStep).filter(
        models.ApprovalStep.document_id == document_id,
        models.ApprovalStep.status != "approved"
    ).count() == 0

    if all_approved:
        document = db.query(models.Document).filter(models.Document.id == document_id).first()
        document.status = models.DocumentStatus.APPROVED

    db.commit()
    db.refresh(approval_step)
    return approval_step

def reject_document(
    db: Session, 
    document_id: int, 
    step_number: int, 
    user_id: int, 
    comment: str = None
):
    approval_step = db.query(models.ApprovalStep).filter(
        models.ApprovalStep.document_id == document_id,
        models.ApprovalStep.step_number == step_number
    ).first()

    if not approval_step:
        raise HTTPException(status_code=404, detail="Approval step not found")

    approval_step.status = "rejected"
    approval_step.approved_by = user_id
    approval_step.comment = comment
    approval_step.timestamp = datetime.utcnow()

    # Mark document as rejected
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    document.status = models.DocumentStatus.REJECTED

    db.commit()
    db.refresh(approval_step)
    return approval_step

def get_user_documents(db: Session, user: models.User):
    """Get documents pending for user's role"""
    return db.query(models.Document).join(models.ApprovalStep).filter(
        models.ApprovalStep.role == user.role,
        models.ApprovalStep.status == "pending"
    ).all()

# ==================== Reports ====================

def generate_report_data(db: Session):
    """Generate report data for dashboard"""
    documents = db.query(models.Document).all()
    
    total_spend = 0
    top_vendors = {}
    
    for doc in documents:
        if doc.extracted_data:
            amount = doc.extracted_data.get("amount", 0)
            total_spend += amount
            vendor = doc.extracted_data.get("vendor", "Unknown")
            top_vendors[vendor] = top_vendors.get(vendor, 0) + amount
    
    # Sort vendors by spend and get top 5
    sorted_vendors = sorted(top_vendors.items(), key=lambda x: x[1], reverse=True)[:5]
    top_vendors_list = [{"name": v, "amount": a} for v, a in sorted_vendors]
    
    # Count pending approvals
    pending_count = db.query(models.ApprovalStep).filter(
        models.ApprovalStep.status == "pending"
    ).count()
    
    return {
        "total_spend": total_spend,
        "total_documents": len(documents),
        "top_vendors": top_vendors_list,
        "pending_count": pending_count
    }