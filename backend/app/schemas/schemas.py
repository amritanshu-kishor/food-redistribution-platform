from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.models import UserRole, UserStatus, OrgVerificationStatus, DonationStatus, AllocationStatus, NotificationType

# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None

# Organization schemas
class OrganizationBase(BaseModel):
    name: str
    description: Optional[str] = None
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    website: Optional[str] = None

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    website: Optional[str] = None

class OrganizationOut(OrganizationBase):
    id: int
    user_id: int
    verification_status: OrgVerificationStatus
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: UserRole

class UserCreate(UserBase):
    password: str
    organization: Optional[OrganizationCreate] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None

class UserOut(UserBase):
    id: int
    status: UserStatus
    created_at: datetime
    organization: Optional[OrganizationOut] = None

    class Config:
        from_attributes = True

# Document schemas
class DocumentOut(BaseModel):
    id: int
    organization_id: int
    document_type: str
    file_name: str
    file_size: int
    content_type: str
    uploaded_at: datetime
    status: OrgVerificationStatus

    class Config:
        from_attributes = True

# Donation schemas
class DonationBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    quantity: float
    unit: str
    prepared_at: datetime
    expires_at: datetime
    pickup_start: datetime
    pickup_end: datetime
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class DonationCreate(DonationBase):
    pass

class DonationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    prepared_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    pickup_start: Optional[datetime] = None
    pickup_end: Optional[datetime] = None
    status: Optional[DonationStatus] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class DonationOut(DonationBase):
    id: int
    donor_id: int
    image_path: Optional[str] = None
    status: DonationStatus
    created_at: datetime
    updated_at: datetime
    donor_name: Optional[str] = None

    class Config:
        from_attributes = True

# Allocation schemas
class AllocationBase(BaseModel):
    requested_quantity: float

class AllocationCreate(AllocationBase):
    donation_id: int

class AllocationOut(BaseModel):
    id: int
    donation_id: int
    receiver_id: int
    requested_quantity: float
    allocated_quantity: float
    status: AllocationStatus
    qr_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    donation: Optional[DonationOut] = None
    receiver_name: Optional[str] = None

    class Config:
        from_attributes = True

# Notification schemas
class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: NotificationType
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

# QR schemas
class QRScanRequest(BaseModel):
    scanned_code: str
    event_type: str  # "PICKUP" or "COMPLETION"

class QRScanResult(BaseModel):
    status: str  # "SUCCESS", "FAILED", "INVALID"
    message: str
    allocation_id: Optional[int] = None
    donation_id: Optional[int] = None

# Audit Log schemas
class AuditLogOut(BaseModel):
    id: int
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    action: str
    target_table: str
    target_id: Optional[int] = None
    timestamp: datetime
    metadata_json: Optional[dict] = None

    class Config:
        from_attributes = True

# Complaint schemas
class ComplaintCreate(BaseModel):
    reported_user_id: Optional[int] = None
    donation_id: Optional[int] = None
    title: str
    description: str

class ComplaintOut(BaseModel):
    id: int
    reporter_id: int
    reporter_name: Optional[str] = None
    reported_user_id: Optional[int] = None
    reported_user_name: Optional[str] = None
    donation_id: Optional[int] = None
    donation_title: Optional[str] = None
    title: str
    description: str
    status: str
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ComplaintResolve(BaseModel):
    status: str  # "resolved" or "ignored"
    resolution_notes: str

# Password changes
class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr
