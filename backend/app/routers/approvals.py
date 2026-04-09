from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas, crud, auth
from datetime import datetime

router = APIRouter(prefix="/approvals", tags=["approvals"])

@router.post("/action", response_model=schemas.ApprovalResponse)
def approval_action(
    action: schemas.ApprovalAction,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # Check if user has permission for this step
    approval_step = db.query(models.ApprovalStep).filter(
        models.ApprovalStep.document_id == action.document_id,
        models.ApprovalStep.step_number == action.step_number
    ).first()

    if not approval_step:
        raise HTTPException(status_code=404, detail="Approval step not found")

    if approval_step.role != current_user.role:
        raise HTTPException(status_code=403, detail="You are not authorized for this approval step")

    if action.action == "approve":
        return crud.approve_document(
            db, action.document_id, action.step_number, current_user.id, action.comment
        )
    elif action.action == "reject":
        return crud.reject_document(
            db, action.document_id, action.step_number, current_user.id, action.comment
        )
    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")

@router.get("/pending")
def get_pending_approvals(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get documents waiting for current user's approval"""
    documents = crud.get_user_documents(db, current_user)
    return documents