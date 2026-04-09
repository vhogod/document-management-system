from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas, crud, utils, auth
import os
import shutil
from datetime import datetime

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=schemas.DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "invoice",
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    if document_type not in ["invoice", "credit_note"]:
        raise HTTPException(status_code=400, detail="Invalid document type")

    # Save file
    file_path = f"{UPLOAD_DIR}/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # AI Extraction
    extracted_data = await utils.extract_invoice_data(file_path)

    # Duplicate check
    duplicate = crud.check_duplicate(
        db, 
        invoice_number=extracted_data.get("invoice_number")
    )

    document = crud.create_document(
        db=db,
        file_path=file_path,
        document_type=document_type,
        extracted_data=extracted_data,
        uploaded_by=current_user.id
    )

    if duplicate:
        document.duplicate = True
        db.commit()

    return document