from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_active_user
from app.crud.crud import verify_qr_scan
from app.models.models import User, QRVerificationType
from app.schemas.schemas import QRScanRequest, QRScanResult

router = APIRouter()

@router.post("/verify", response_model=QRScanResult)
def scan_qr_code(
    req: QRScanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Verify an NGO's pickup or completion scan code."""
    try:
        event = QRVerificationType(req.event_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid event_type. Allowed values are 'PICKUP' or 'COMPLETION'."
        )
        
    return verify_qr_scan(db, req.scanned_code, event, current_user.id)
