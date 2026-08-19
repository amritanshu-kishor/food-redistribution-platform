from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_user
from app.crud.crud import update_user, create_org_document, create_audit_log
from app.models.models import User, Organization
from app.schemas.schemas import UserOut, UserUpdate
from app.utils.storage import save_uploaded_file

router = APIRouter()

@router.get("/profile", response_model=UserOut)
def get_profile(
    current_user: User = Depends(get_current_user)
):
    """Retrieve logged-in user profile, role, and organization status."""
    return current_user

@router.put("/profile", response_model=UserOut)
def update_profile(
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update profile attributes for the logged-in user."""
    return update_user(db, current_user, user_in)

@router.post("/documents")
def upload_verification_document(
    doc_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload a verification PDF/image document for the associated organization."""
    if not current_user.organization:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must have an associated organization to upload documents."
        )
        
    # Read file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    file_path = save_uploaded_file(file, is_image=False)
    
    doc = create_org_document(
        db,
        organization_id=current_user.organization.id,
        doc_type=doc_type,
        file_path=file_path,
        file_name=file.filename,
        file_size=file_size,
        content_type=file.content_type
    )
    
    create_audit_log(
        db,
        actor_id=current_user.id,
        action="user_upload_document",
        target_table="organization_documents",
        target_id=doc.id
    )
    return {
        "detail": "Document uploaded successfully and is pending admin review.",
        "document_id": doc.id,
        "file_path": file_path
    }
