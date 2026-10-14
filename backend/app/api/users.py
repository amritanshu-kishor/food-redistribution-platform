from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_user
from app.crud.crud import update_user, create_org_document, create_audit_log, create_complaint
from app.models.models import User, UserRole
from app.schemas.schemas import UserOut, UserUpdate, ComplaintCreate, ComplaintOut
from app.utils.storage import delete_uploaded_file, save_uploaded_file

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
        
    allowed_doc_types = (
        {"business_license", "food_permit"}
        if current_user.role == UserRole.RESTAURANT
        else {"tax_exemption", "ngo_license", "audit_statement"}
    )
    if doc_type not in allowed_doc_types:
        raise HTTPException(status_code=400, detail="Invalid document type for this account")

    file_path = save_uploaded_file(file, is_image=False)
    file_size = file.file.tell()
    
    try:
        doc = create_org_document(
            db,
            organization_id=current_user.organization.id,
            doc_type=doc_type,
            file_path=file_path,
            file_name=file.filename,
            file_size=file_size,
            content_type=file.content_type,
        )
    except Exception:
        delete_uploaded_file(file_path)
        raise
    
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
    }


@router.post("/complaints", response_model=ComplaintOut, status_code=status.HTTP_201_CREATED)
def submit_complaint(
    complaint_in: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Allow an involved partner to submit a complaint for admin review."""
    complaint = create_complaint(
        db,
        reporter_id=current_user.id,
        reported_user_id=complaint_in.reported_user_id,
        donation_id=complaint_in.donation_id,
        title=complaint_in.title,
        description=complaint_in.description,
    )
    complaint.reporter_name = current_user.full_name
    return complaint
