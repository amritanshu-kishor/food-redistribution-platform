import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text, Enum, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    RESTAURANT = "restaurant"
    NGO = "ngo"

class UserStatus(str, enum.Enum):
    ACTIVE = "active"
    PENDING = "pending"
    SUSPENDED = "suspended"
    REJECTED = "rejected"
    DEACTIVATED = "deactivated"

class OrgVerificationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class DonationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    AVAILABLE = "AVAILABLE"
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    PICKUP_PENDING = "PICKUP_PENDING"
    PICKED_UP = "PICKED_UP"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    PICKUP_FAILED = "PICKUP_FAILED"

class AllocationStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    ACCEPTED = "ACCEPTED"
    PICKED_UP = "PICKED_UP"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"

class QRVerificationType(str, enum.Enum):
    PICKUP = "PICKUP"
    COMPLETION = "COMPLETION"

class NotificationType(str, enum.Enum):
    SYSTEM = "SYSTEM"
    DONATION = "DONATION"
    CLAIM = "CLAIM"
    VERIFICATION = "VERIFICATION"
    ALERT = "ALERT"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    tokens = relationship("AuthToken", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="actor")
    reports_submitted = relationship("ReportComplaint", foreign_keys="ReportComplaint.reporter_id", back_populates="reporter")
    reports_received = relationship("ReportComplaint", foreign_keys="ReportComplaint.reported_user_id", back_populates="reported_user")

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    website = Column(String, nullable=True)
    verification_status = Column(Enum(OrgVerificationStatus), default=OrgVerificationStatus.PENDING, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="organization")
    documents = relationship("OrganizationDocument", back_populates="organization", cascade="all, delete-orphan")
    donations = relationship("Donation", back_populates="donor", cascade="all, delete-orphan")
    allocations = relationship("DonationAllocation", back_populates="receiver", cascade="all, delete-orphan")

class OrganizationDocument(Base):
    __tablename__ = "organization_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    document_type = Column(String, nullable=False)  # e.g., "business_license", "ngo_registration"
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    content_type = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(Enum(OrgVerificationStatus), default=OrgVerificationStatus.PENDING, nullable=False)
    
    # Relationships
    organization = relationship("Organization", back_populates="documents")

class Donation(Base):
    __tablename__ = "donations"
    
    id = Column(Integer, primary_key=True, index=True)
    donor_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    image_path = Column(String, nullable=True)
    category = Column(String, index=True, nullable=False)  # e.g., "Prepared Meals", "Produce", "Bakery"
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)  # e.g., "kg", "portions", "boxes"
    prepared_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)
    pickup_start = Column(DateTime, nullable=False)
    pickup_end = Column(DateTime, nullable=False)
    status = Column(Enum(DonationStatus), default=DonationStatus.DRAFT, nullable=False, index=True)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    donor = relationship("Organization", back_populates="donations")
    allocations = relationship("DonationAllocation", back_populates="donation", cascade="all, delete-orphan")
    qr_events = relationship("QRVerificationEvent", back_populates="donation", cascade="all, delete-orphan")
    reports = relationship("ReportComplaint", back_populates="donation")

class DonationAllocation(Base):
    __tablename__ = "donation_allocations"
    
    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("donations.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    requested_quantity = Column(Float, nullable=False)
    allocated_quantity = Column(Float, nullable=False)
    status = Column(Enum(AllocationStatus), default=AllocationStatus.REQUESTED, nullable=False)
    qr_token = Column(String, unique=True, index=True, nullable=True)  # Secure QR reference token
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    donation = relationship("Donation", back_populates="allocations")
    receiver = relationship("Organization", back_populates="allocations")
    qr_events = relationship("QRVerificationEvent", back_populates="allocation", cascade="all, delete-orphan")

class Notification(Base):
    __tablename__ = "notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(Enum(NotificationType), default=NotificationType.SYSTEM, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="notifications")

class QRVerificationEvent(Base):
    __tablename__ = "qr_verification_events"
    
    id = Column(Integer, primary_key=True, index=True)
    donation_id = Column(Integer, ForeignKey("donations.id"), nullable=False)
    allocation_id = Column(Integer, ForeignKey("donation_allocations.id"), nullable=True)
    event_type = Column(Enum(QRVerificationType), nullable=False)
    scanned_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scanned_code = Column(String, nullable=False)
    status = Column(String, nullable=False)  # "SUCCESS", "FAILED", "INVALID"
    error_message = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    donation = relationship("Donation", back_populates="qr_events")
    allocation = relationship("DonationAllocation", back_populates="qr_events")
    scanned_by = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False, index=True)  # e.g., "user_register", "donation_create", "verify_approve"
    target_table = Column(String, nullable=False)  # e.g., "users", "donations"
    target_id = Column(Integer, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    metadata_json = Column(JSON, nullable=True)  # Stores JSON metadata
    
    # Relationships
    actor = relationship("User", back_populates="audit_logs")

class AuthToken(Base):
    __tablename__ = "auth_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    token_type = Column(String, default="refresh", nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="tokens")

class ReportComplaint(Base):
    __tablename__ = "reports_complaints"
    
    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reported_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    donation_id = Column(Integer, ForeignKey("donations.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, default="pending", nullable=False)  # "pending", "resolved", "ignored"
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    reporter = relationship("User", foreign_keys=[reporter_id], back_populates="reports_submitted")
    reported_user = relationship("User", foreign_keys=[reported_user_id], back_populates="reports_received")
    donation = relationship("Donation", back_populates="reports")
