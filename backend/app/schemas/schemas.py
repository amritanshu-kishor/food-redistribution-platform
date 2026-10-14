from datetime import datetime, timezone
from typing import Annotated, List, Optional, Literal
from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, field_serializer, field_validator, model_validator
from app.models.models import UserRole, UserStatus, OrgVerificationStatus, DonationStatus, AllocationStatus, NotificationType

def validate_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return value

Password = Annotated[str, Field(min_length=12, max_length=72), AfterValidator(validate_password_bytes)]

def utc_naive(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value

class InputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class OutputModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_utc(self, value):
        # Database timestamps are UTC-naive. Include the zone on the wire so
        # browsers do not interpret them as local wall-clock time.
        if isinstance(value, datetime):
            return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
        return value

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
    name: str = Field(..., min_length=2, max_length=160)
    description: Optional[str] = Field(None, max_length=2000)
    address: str = Field(..., min_length=3, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    website: Optional[str] = Field(None, max_length=2048)

    @field_validator("website")
    @classmethod
    def validate_website(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.lower().startswith(("http://", "https://")):
            raise ValueError("website must use http:// or https://")
        return value

class OrganizationCreate(OrganizationBase):
    pass

class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    website: Optional[str] = None

class OrganizationOut(OrganizationBase, OutputModel):
    id: int
    user_id: int
    verification_status: OrgVerificationStatus
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=160)
    phone: Optional[str] = Field(None, min_length=7, max_length=40)
    role: UserRole

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

class UserCreate(UserBase, InputModel):
    password: Password
    organization: Optional[OrganizationCreate] = None

    @model_validator(mode="after")
    def public_roles_only(self):
        if self.role == UserRole.ADMIN:
            raise ValueError("Administrator accounts are created by the server bootstrap only")
        if self.organization is None:
            raise ValueError("organization is required for partner accounts")
        return self

class UserUpdate(InputModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=160)
    phone: Optional[str] = Field(None, min_length=7, max_length=40)

class UserOut(UserBase, OutputModel):
    id: int
    status: UserStatus
    created_at: datetime
    organization: Optional[OrganizationOut] = None

    model_config = ConfigDict(from_attributes=True)

# Document schemas
class DocumentOut(OutputModel):
    id: int
    organization_id: int
    document_type: str
    file_name: str
    file_size: int
    content_type: str
    uploaded_at: datetime
    status: OrgVerificationStatus

    model_config = ConfigDict(from_attributes=True)

# Donation schemas
class DonationBase(BaseModel):
    title: str = Field(..., min_length=2, max_length=160)
    description: Optional[str] = Field(None, max_length=4000)
    category: str = Field(..., min_length=2, max_length=80)
    quantity: float = Field(..., gt=0, le=1_000_000)
    unit: str = Field(..., min_length=1, max_length=40)
    prepared_at: datetime
    expires_at: datetime
    pickup_start: datetime
    pickup_end: datetime
    address: str = Field(..., min_length=3, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    @field_validator("prepared_at", "expires_at", "pickup_start", "pickup_end")
    @classmethod
    def normalize_time(cls, value):
        return utc_naive(value)

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.expires_at <= self.prepared_at:
            raise ValueError("expires_at must be after prepared_at")
        if self.pickup_start < self.prepared_at:
            raise ValueError("pickup_start cannot be before prepared_at")
        if self.pickup_end <= self.pickup_start:
            raise ValueError("pickup_end must be after pickup_start")
        if self.pickup_end > self.expires_at:
            raise ValueError("pickup_end cannot be after expires_at")
        return self

class DonationCreate(DonationBase, InputModel):
    pass

class DonationUpdate(InputModel):
    title: Optional[str] = Field(None, min_length=2, max_length=160)
    description: Optional[str] = Field(None, max_length=4000)
    category: Optional[str] = Field(None, min_length=2, max_length=80)
    quantity: Optional[float] = Field(None, gt=0, le=1_000_000)
    unit: Optional[str] = Field(None, min_length=1, max_length=40)
    prepared_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    pickup_start: Optional[datetime] = None
    pickup_end: Optional[datetime] = None
    status: Optional[DonationStatus] = None
    address: Optional[str] = Field(None, min_length=3, max_length=500)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    @field_validator("prepared_at", "expires_at", "pickup_start", "pickup_end")
    @classmethod
    def normalize_time(cls, value):
        return utc_naive(value)

    @model_validator(mode="after")
    def reject_required_nulls(self):
        nullable = {"description", "latitude", "longitude"}
        if any(key in self.model_fields_set and getattr(self, key) is None for key in self.model_fields_set - nullable):
            raise ValueError("Required listing fields cannot be null")
        return self

class DonationOut(OutputModel):
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
    id: int
    donor_id: int
    image_path: Optional[str] = None
    status: DonationStatus
    created_at: datetime
    updated_at: datetime
    donor_name: Optional[str] = None
    available_quantity: float = 0

    model_config = ConfigDict(from_attributes=True)

# Allocation schemas
class AllocationBase(BaseModel):
    requested_quantity: float = Field(..., gt=0, le=1_000_000)

class AllocationCreate(AllocationBase, InputModel):
    donation_id: int = Field(gt=0)

class AllocationOut(OutputModel):
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

    model_config = ConfigDict(from_attributes=True)

# Notification schemas
class NotificationOut(OutputModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: NotificationType
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# QR schemas
class QRScanRequest(BaseModel):
    scanned_code: str = Field(..., min_length=8, max_length=256)
    event_type: Literal["PICKUP", "COMPLETION"]

class QRScanResult(BaseModel):
    status: str  # "SUCCESS", "FAILED", "INVALID"
    message: str
    allocation_id: Optional[int] = None
    donation_id: Optional[int] = None

# Audit Log schemas
class AuditLogOut(OutputModel):
    id: int
    actor_id: Optional[int] = None
    actor_name: Optional[str] = None
    action: str
    target_table: str
    target_id: Optional[int] = None
    timestamp: datetime
    metadata_json: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)

# Complaint schemas
class ComplaintCreate(BaseModel):
    reported_user_id: Optional[int] = None
    donation_id: Optional[int] = None
    title: str = Field(..., min_length=3, max_length=160)
    description: str = Field(..., min_length=5, max_length=4000)

class ComplaintOut(OutputModel):
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

    model_config = ConfigDict(from_attributes=True)

class ComplaintResolve(BaseModel):
    status: Literal["resolved", "ignored"]
    resolution_notes: str = Field(..., min_length=1, max_length=4000)

# Password changes
class ChangePasswordRequest(InputModel):
    old_password: str = Field(..., min_length=1, max_length=128)
    new_password: Password

class ResetPasswordRequest(InputModel):
    token: str = Field(..., min_length=16, max_length=256)
    new_password: Password

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=16, max_length=4096)
