import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import get_password_hash
from app.models.models import (
    User, UserRole, UserStatus, Organization, OrgVerificationStatus, OrganizationDocument,
    Donation, DonationStatus, DonationAllocation, AllocationStatus,
    Notification, NotificationType, QRVerificationEvent, QRVerificationType, AuditLog, ReportComplaint
)
from app.schemas.schemas import UserCreate, UserUpdate, DonationCreate, DonationUpdate, AllocationCreate, QRScanResult
from app.utils.notifications import create_notification

# =========================================================================
# AUDIT LOG UTILITY
# =========================================================================
def create_audit_log(
    db: Session,
    actor_id: Optional[int],
    action: str,
    target_table: str,
    target_id: Optional[int],
    metadata_json: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """Record an audit log entry in the database."""
    log_entry = AuditLog(
        actor_id=actor_id,
        action=action,
        target_table=target_table,
        target_id=target_id,
        metadata_json=metadata_json
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    return log_entry

# =========================================================================
# AUTHENTICATION & USER SERVICES
# =========================================================================
def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user_in: UserCreate) -> User:
    """Create user and associate with a pending organization if not admin."""
    hashed_pwd = get_password_hash(user_in.password)
    
    # Admin is active by default; restaurants/NGOs are pending until approved
    initial_status = UserStatus.ACTIVE if user_in.role == UserRole.ADMIN else UserStatus.PENDING
    
    db_user = User(
        email=user_in.email,
        hashed_password=hashed_pwd,
        role=user_in.role,
        full_name=user_in.full_name,
        phone=user_in.phone,
        status=initial_status
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create matching organization details
    if user_in.role != UserRole.ADMIN and user_in.organization:
        db_org = Organization(
            user_id=db_user.id,
            name=user_in.organization.name,
            description=user_in.organization.description,
            address=user_in.organization.address,
            latitude=user_in.organization.latitude,
            longitude=user_in.organization.longitude,
            website=user_in.organization.website,
            verification_status=OrgVerificationStatus.PENDING,
            is_verified=False
        )
        db.add(db_org)
        db.commit()
        db.refresh(db_org)
        
    # Record Audit Log
    create_audit_log(
        db, 
        actor_id=db_user.id, 
        action="user_register", 
        target_table="users", 
        target_id=db_user.id,
        metadata_json={"role": user_in.role.value}
    )
    
    # Notify admins of new registration
    if user_in.role != UserRole.ADMIN:
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        for admin in admins:
            create_notification(
                db,
                user_id=admin.id,
                title="New Registration Pending Review",
                message=f"{user_in.full_name} has registered a {user_in.role.value} account and is pending verification.",
                notification_type=NotificationType.VERIFICATION
            )
            
    return db_user

def update_user(db: Session, db_user: User, user_in: UserUpdate) -> User:
    if user_in.full_name is not None:
        db_user.full_name = user_in.full_name
    if user_in.phone is not None:
        db_user.phone = user_in.phone
    if user_in.password is not None:
        db_user.hashed_password = get_password_hash(user_in.password)
    db.commit()
    db.refresh(db_user)
    return db_user

# =========================================================================
# DOCUMENT VERIFICATION & ADMIN CONTROL
# =========================================================================
def create_org_document(
    db: Session,
    organization_id: int,
    doc_type: str,
    file_path: str,
    file_name: str,
    file_size: int,
    content_type: str
) -> OrganizationDocument:
    db_doc = OrganizationDocument(
        organization_id=organization_id,
        document_type=doc_type,
        file_path=file_path,
        file_name=file_name,
        file_size=file_size,
        content_type=content_type,
        status=OrgVerificationStatus.PENDING
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    
    # Notify Admin
    org = db.query(Organization).filter(Organization.id == organization_id).first()
    if org:
        admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
        for admin in admins:
            create_notification(
                db,
                user_id=admin.id,
                title="Verification Document Uploaded",
                message=f"Organization '{org.name}' has uploaded a {doc_type} document for verification.",
                notification_type=NotificationType.VERIFICATION
            )
            
    return db_doc

def verify_organization(
    db: Session,
    org_id: int,
    status_choice: OrgVerificationStatus,
    admin_id: int
) -> Organization:
    """Approve or reject an organization's verification state."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
        
    org.verification_status = status_choice
    org.is_verified = (status_choice == OrgVerificationStatus.APPROVED)
    
    # Update associated user status
    user = db.query(User).filter(User.id == org.user_id).first()
    if user:
        if status_choice == OrgVerificationStatus.APPROVED:
            user.status = UserStatus.ACTIVE
            title = "Account Verified"
            msg = "Congratulations! Your account has been verified and you can now start donating/claiming food."
        else:
            user.status = UserStatus.REJECTED
            title = "Verification Rejected"
            msg = "Your organization verification request was rejected. Please contact support or update your documents."
            
        create_notification(db, user_id=user.id, title=title, message=msg, notification_type=NotificationType.VERIFICATION)
        
    db.commit()
    db.refresh(org)
    
    create_audit_log(
        db,
        actor_id=admin_id,
        action=f"org_verify_{status_choice.value}",
        target_table="organizations",
        target_id=org.id
    )
    return org

def update_user_status(db: Session, user_id: int, new_status: UserStatus, admin_id: int) -> User:
    """Suspend or reactivate a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.status = new_status
    if new_status == UserStatus.ACTIVE and user.organization:
        user.organization.verification_status = OrgVerificationStatus.APPROVED
        user.organization.is_verified = True
    db.commit()
    db.refresh(user)
    
    create_notification(
        db,
        user_id=user.id,
        title=f"Account Status Updated",
        message=f"Your account status has been updated to {new_status.value}.",
        notification_type=NotificationType.SYSTEM
    )
    
    create_audit_log(
        db,
        actor_id=admin_id,
        action=f"user_status_{new_status.value}",
        target_table="users",
        target_id=user.id
    )
    return user

# =========================================================================
# DONATION SERVICES & LIFE CYCLE
# =========================================================================
def check_donation_transition(current: DonationStatus, target: DonationStatus) -> bool:
    """Enforce valid backend state transitions for donations."""
    valid = {
        DonationStatus.DRAFT: {DonationStatus.AVAILABLE, DonationStatus.CANCELLED},
        DonationStatus.AVAILABLE: {DonationStatus.REQUESTED, DonationStatus.CANCELLED, DonationStatus.EXPIRED},
        DonationStatus.REQUESTED: {DonationStatus.ACCEPTED, DonationStatus.AVAILABLE, DonationStatus.CANCELLED, DonationStatus.EXPIRED},
        DonationStatus.ACCEPTED: {DonationStatus.PICKUP_PENDING, DonationStatus.CANCELLED, DonationStatus.EXPIRED, DonationStatus.PICKUP_FAILED},
        DonationStatus.PICKUP_PENDING: {DonationStatus.PICKED_UP, DonationStatus.PICKUP_FAILED, DonationStatus.CANCELLED},
        DonationStatus.PICKED_UP: {DonationStatus.COMPLETED, DonationStatus.PICKUP_FAILED},
        DonationStatus.COMPLETED: set(),
        DonationStatus.CANCELLED: set(),
        DonationStatus.EXPIRED: set(),
        DonationStatus.REJECTED: set(),
        DonationStatus.PICKUP_FAILED: set()
    }
    return target in valid.get(current, set())

def create_donation(db: Session, donation_in: DonationCreate, donor_org_id: int) -> Donation:
    """Create a new donation in DRAFT status."""
    # Check if donor is verified
    org = db.query(Organization).filter(Organization.id == donor_org_id).first()
    if not org or not org.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only verified organization accounts can post donations."
        )
        
    db_donation = Donation(
        donor_id=donor_org_id,
        title=donation_in.title,
        description=donation_in.description,
        category=donation_in.category,
        quantity=donation_in.quantity,
        unit=donation_in.unit,
        prepared_at=donation_in.prepared_at,
        expires_at=donation_in.expires_at,
        pickup_start=donation_in.pickup_start,
        pickup_end=donation_in.pickup_end,
        address=donation_in.address,
        latitude=donation_in.latitude,
        longitude=donation_in.longitude,
        status=DonationStatus.DRAFT
    )
    db.add(db_donation)
    db.commit()
    db.refresh(db_donation)
    
    create_audit_log(
        db,
        actor_id=org.user_id,
        action="donation_create",
        target_table="donations",
        target_id=db_donation.id
    )
    return db_donation

def update_donation(db: Session, donation_id: int, donation_in: DonationUpdate, actor_user_id: int) -> Donation:
    """Update donation details or transition state, validating changes."""
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
        
    user = db.query(User).filter(User.id == actor_user_id).first()
    is_admin = user and user.role == UserRole.ADMIN
    if donation.donor.user_id != actor_user_id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorized to modify this donation")
        
    # Check status transition validity if updated
    if donation_in.status is not None and donation_in.status != donation.status:
        if not check_donation_transition(donation.status, donation_in.status):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid donation status transition from {donation.status.value} to {donation_in.status.value}"
            )
        donation.status = donation_in.status
        
    # Update other fields
    update_data = donation_in.model_dump(exclude_unset=True)
    if "status" in update_data:
        del update_data["status"]
        
    for k, v in update_data.items():
        setattr(donation, k, v)
        
    db.commit()
    db.refresh(donation)
    
    # Audit log
    create_audit_log(
        db,
        actor_id=actor_user_id,
        action="donation_update",
        target_table="donations",
        target_id=donation.id,
        metadata_json={"status": donation.status.value}
    )
    return donation

def auto_expire_donations(db: Session) -> int:
    """Enforce expiration limits. Changes AVAILABLE or REQUESTED donations to EXPIRED if past expires_at."""
    now = datetime.utcnow()
    expired_donations = db.query(Donation).filter(
        and_(
            Donation.status.in_([DonationStatus.AVAILABLE, DonationStatus.REQUESTED]),
            Donation.expires_at < now
        )
    ).all()
    
    count = 0
    for donation in expired_donations:
        donation.status = DonationStatus.EXPIRED
        count += 1
        
        # Notify donor
        create_notification(
            db,
            user_id=donation.donor.user_id,
            title="Donation Expired",
            message=f"Your donation '{donation.title}' has expired without being fully allocated.",
            notification_type=NotificationType.ALERT
        )
        
        # Fail any open pending requests
        for alloc in donation.allocations:
            if alloc.status == AllocationStatus.REQUESTED:
                alloc.status = AllocationStatus.FAILED
                # Notify NGO
                create_notification(
                    db,
                    user_id=alloc.receiver.user_id,
                    title="Claim Request Failed",
                    message=f"The donation '{donation.title}' you requested has expired.",
                    notification_type=NotificationType.ALERT
                )
                
        create_audit_log(
            db,
            actor_id=None,
            action="donation_auto_expire",
            target_table="donations",
            target_id=donation.id
        )
        
    if count > 0:
        db.commit()
    return count

# =========================================================================
# ALLOCATION & LOCKING SERVICES (RACE CONDITION PROTECTION)
# =========================================================================
def calculate_remaining_quantity(donation: Donation) -> float:
    """Calculate remaining unallocated quantity for a donation."""
    allocated = sum(
        alloc.allocated_quantity for alloc in donation.allocations
        if alloc.status in [AllocationStatus.ACCEPTED, AllocationStatus.PICKED_UP, AllocationStatus.COMPLETED]
    )
    return max(0.0, donation.quantity - allocated)

def calculate_remaining_available_quantity(donation: Donation) -> float:
    """Calculate remaining available quantity including pending requests."""
    allocated = sum(
        alloc.allocated_quantity for alloc in donation.allocations
        if alloc.status in [AllocationStatus.ACCEPTED, AllocationStatus.PICKED_UP, AllocationStatus.COMPLETED]
    )
    pending = sum(
        alloc.requested_quantity for alloc in donation.allocations
        if alloc.status == AllocationStatus.REQUESTED
    )
    return max(0.0, donation.quantity - allocated - pending)

def create_allocation(db: Session, alloc_in: AllocationCreate, receiver_org_id: int) -> DonationAllocation:
    """NGO claims a portion of an available donation. Uses transaction locks."""
    # 1. Lock the Donation row using FOR UPDATE to prevent race conditions
    donation = db.query(Donation).filter(Donation.id == alloc_in.donation_id).with_for_update().first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
        
    # Check NGO eligibility
    receiver = db.query(Organization).filter(Organization.id == receiver_org_id).first()
    if not receiver or not receiver.is_verified:
        raise HTTPException(status_code=403, detail="Only verified NGOs can request allocations.")
        
    # Check if expired
    if donation.expires_at < datetime.utcnow() or donation.status == DonationStatus.EXPIRED:
        raise HTTPException(status_code=400, detail="This donation has expired and cannot be claimed.")
        
    # Check status
    if donation.status not in [DonationStatus.AVAILABLE, DonationStatus.REQUESTED]:
        raise HTTPException(status_code=400, detail="Donation is not available for claims.")
        
    # Calculate available quantity including pending requests to avoid over-requesting
    remaining = calculate_remaining_available_quantity(donation)
    if alloc_in.requested_quantity <= 0 or alloc_in.requested_quantity > remaining:
        raise HTTPException(
            status_code=400,
            detail=f"Requested quantity exceeds remaining available quantity ({remaining} {donation.unit})."
        )
        
    # Create the allocation request (allocated_quantity is 0 until approved)
    allocation = DonationAllocation(
        donation_id=donation.id,
        receiver_id=receiver_org_id,
        requested_quantity=alloc_in.requested_quantity,
        allocated_quantity=0,
        status=AllocationStatus.REQUESTED
    )
    db.add(allocation)
    
    # Transition donation status to REQUESTED
    if donation.status == DonationStatus.AVAILABLE:
        donation.status = DonationStatus.REQUESTED
        
    db.commit()
    db.refresh(allocation)
    
    # Notify donor
    create_notification(
        db,
        user_id=donation.donor.user_id,
        title="New Food Claim Request",
        message=f"NGO '{receiver.name}' is requesting {alloc_in.requested_quantity} {donation.unit} of '{donation.title}'.",
        notification_type=NotificationType.CLAIM
    )
    
    # Audit log
    create_audit_log(
        db,
        actor_id=receiver.user_id,
        action="claim_request",
        target_table="donation_allocations",
        target_id=allocation.id,
        metadata_json={"quantity": alloc_in.requested_quantity}
    )
    return allocation

def accept_allocation(db: Session, allocation_id: int, actor_user_id: int) -> DonationAllocation:
    """Restaurant approves the NGO claim. Updates allocated quantity and locks it."""
    # Lock the donation associated with the allocation
    allocation = db.query(DonationAllocation).filter(DonationAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
        
    donation = db.query(Donation).filter(Donation.id == allocation.donation_id).with_for_update().first()
    if donation.donor.user_id != actor_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to manage this donation's claims")
        
    if allocation.status != AllocationStatus.REQUESTED:
        raise HTTPException(status_code=400, detail="Can only accept pending requests")
        
    # Verify quantity is still available
    remaining = calculate_remaining_quantity(donation)
    if allocation.requested_quantity > remaining:
        allocation.status = AllocationStatus.FAILED
        db.commit()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot accept claim. Remaining available quantity is only {remaining}."
        )
        
    # Grant allocation
    allocation.allocated_quantity = allocation.requested_quantity
    allocation.status = AllocationStatus.ACCEPTED
    # Generate secure QR token reference
    allocation.qr_token = f"claim_{uuid.uuid4().hex}"
    
    # Check if remaining quantity becomes 0. If so, update donation status
    new_remaining = calculate_remaining_quantity(donation)
    if new_remaining <= 0:
        donation.status = DonationStatus.ACCEPTED
        
    db.commit()
    db.refresh(allocation)
    
    # Notify NGO
    create_notification(
        db,
        user_id=allocation.receiver.user_id,
        title="Food Claim Approved",
        message=f"Your claim for {allocation.allocated_quantity} {donation.unit} of '{donation.title}' was approved! You can pick it up now.",
        notification_type=NotificationType.CLAIM
    )
    
    # Audit log
    create_audit_log(
        db,
        actor_id=actor_user_id,
        action="claim_approve",
        target_table="donation_allocations",
        target_id=allocation.id,
        metadata_json={"allocated": allocation.allocated_quantity}
    )
    return allocation

def reject_allocation(db: Session, allocation_id: int, actor_user_id: int) -> DonationAllocation:
    """Reject an NGO's claim."""
    allocation = db.query(DonationAllocation).filter(DonationAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
        
    donation = db.query(Donation).filter(Donation.id == allocation.donation_id).first()
    if donation.donor.user_id != actor_user_id:
        raise HTTPException(status_code=403, detail="Not authorized to reject this claim")
        
    if allocation.status != AllocationStatus.REQUESTED:
        raise HTTPException(status_code=400, detail="Can only reject pending requests")
        
    allocation.status = AllocationStatus.REJECTED
    
    # If no pending requests left and unallocated quantity > 0, set status back to AVAILABLE
    pending_count = db.query(DonationAllocation).filter(
        and_(
            DonationAllocation.donation_id == donation.id,
            DonationAllocation.status == AllocationStatus.REQUESTED
        )
    ).count()
    if pending_count == 0 and calculate_remaining_quantity(donation) > 0:
        donation.status = DonationStatus.AVAILABLE
        
    db.commit()
    db.refresh(allocation)
    
    # Notify NGO
    create_notification(
        db,
        user_id=allocation.receiver.user_id,
        title="Food Claim Request Declined",
        message=f"Your request for '{donation.title}' has been declined by the donor.",
        notification_type=NotificationType.CLAIM
    )
    
    # Audit
    create_audit_log(
        db,
        actor_id=actor_user_id,
        action="claim_reject",
        target_table="donation_allocations",
        target_id=allocation.id
    )
    return allocation

# =========================================================================
# QR SCANNING VERIFICATION
# =========================================================================
def verify_qr_scan(db: Session, scanned_code: str, event_type: QRVerificationType, actor_id: int) -> QRScanResult:
    """Scan and process QR code to confirm pickup or completion."""
    # Find allocation associated with the qr_token
    allocation = db.query(DonationAllocation).filter(DonationAllocation.qr_token == scanned_code).first()
    actor = db.query(User).filter(User.id == actor_id).first()
    
    if not allocation:
        # Create failure audit log
        QRVerificationEvent(
            donation_id=0,
            event_type=event_type,
            scanned_by_id=actor_id,
            scanned_code=scanned_code,
            status="INVALID",
            error_message="Invalid QR Code reference."
        )
        db.commit()
        return QRScanResult(status="INVALID", message="Invalid QR code reference token.")
        
    donation = allocation.donation
    
    # Transition validation
    if event_type == QRVerificationType.PICKUP:
        # Confirming pickup: Done by the Restaurant (donor) scanning the NGO's QR code
        # Or NGO scanning Restaurant QR. To make it flexible: anyone involved can confirm.
        # Let's ensure the user scanning is either the donor or the receiver
        if actor.organization.id not in [donation.donor_id, allocation.receiver_id]:
            raise HTTPException(status_code=403, detail="You are not authorized to verify this transaction.")
            
        if allocation.status != AllocationStatus.ACCEPTED:
            return QRScanResult(
                status="FAILED",
                message=f"Cannot confirm pickup. Current status is {allocation.status.value} instead of ACCEPTED.",
                allocation_id=allocation.id
            )
            
        # Update Allocation Status
        allocation.status = AllocationStatus.PICKED_UP
        
        # Update Donation aggregate status
        # If all allocations are accepted/picked up, move donation to PICKED_UP
        non_final_allocs = db.query(DonationAllocation).filter(
            and_(
                DonationAllocation.donation_id == donation.id,
                DonationAllocation.status.in_([AllocationStatus.REQUESTED, AllocationStatus.ACCEPTED])
            )
        ).count()
        if non_final_allocs == 0:
            donation.status = DonationStatus.PICKED_UP
        else:
            donation.status = DonationStatus.PICKUP_PENDING
            
        # Record successful event
        event = QRVerificationEvent(
            donation_id=donation.id,
            allocation_id=allocation.id,
            event_type=event_type,
            scanned_by_id=actor_id,
            scanned_code=scanned_code,
            status="SUCCESS"
        )
        db.add(event)
        
        # Notify NGO & Restaurant
        create_notification(
            db,
            user_id=allocation.receiver.user_id,
            title="Food Handover Confirmed",
            message=f"Pickup of {allocation.allocated_quantity} {donation.unit} of '{donation.title}' has been successfully verified via QR.",
            notification_type=NotificationType.CLAIM
        )
        create_notification(
            db,
            user_id=donation.donor.user_id,
            title="Food Picked Up",
            message=f"NGO has picked up {allocation.allocated_quantity} {donation.unit} of '{donation.title}'.",
            notification_type=NotificationType.CLAIM
        )
        
        db.commit()
        
        create_audit_log(
            db,
            actor_id=actor_id,
            action="qr_verify_pickup",
            target_table="donation_allocations",
            target_id=allocation.id
        )
        return QRScanResult(
            status="SUCCESS",
            message="Food pickup verified successfully! Status is now PICKED_UP.",
            allocation_id=allocation.id,
            donation_id=donation.id
        )
        
    elif event_type == QRVerificationType.COMPLETION:
        # Confirming completion: NGO arrived and completed distribution/handover.
        if actor.organization.id not in [donation.donor_id, allocation.receiver_id]:
            raise HTTPException(status_code=403, detail="You are not authorized to verify this transaction.")
            
        if allocation.status != AllocationStatus.PICKED_UP:
            return QRScanResult(
                status="FAILED",
                message=f"Cannot confirm completion. Status is {allocation.status.value} instead of PICKED_UP.",
                allocation_id=allocation.id
            )
            
        allocation.status = AllocationStatus.COMPLETED
        
        # If all allocations for the donation are completed, transition donation to COMPLETED
        active_allocs = db.query(DonationAllocation).filter(
            and_(
                DonationAllocation.donation_id == donation.id,
                DonationAllocation.status != AllocationStatus.COMPLETED,
                DonationAllocation.status != AllocationStatus.CANCELLED,
                DonationAllocation.status != AllocationStatus.REJECTED
            )
        ).count()
        if active_allocs == 0:
            donation.status = DonationStatus.COMPLETED
            
        event = QRVerificationEvent(
            donation_id=donation.id,
            allocation_id=allocation.id,
            event_type=event_type,
            scanned_by_id=actor_id,
            scanned_code=scanned_code,
            status="SUCCESS"
        )
        db.add(event)
        
        create_notification(
            db,
            user_id=allocation.receiver.user_id,
            title="Distribution Completed",
            message=f"Your delivery completion for '{donation.title}' is confirmed. Thank you for your impact!",
            notification_type=NotificationType.CLAIM
        )
        create_notification(
            db,
            user_id=donation.donor.user_id,
            title="Donation Completed",
            message=f"Distribution of your food donation '{donation.title}' has been successfully completed.",
            notification_type=NotificationType.CLAIM
        )
        
        db.commit()
        
        create_audit_log(
            db,
            actor_id=actor_id,
            action="qr_verify_completion",
            target_table="donation_allocations",
            target_id=allocation.id
        )
        return QRScanResult(
            status="SUCCESS",
            message="Food distribution completed successfully! Status is now COMPLETED.",
            allocation_id=allocation.id,
            donation_id=donation.id
        )
        
    return QRScanResult(status="INVALID", message="Invalid QR event type.")

# =========================================================================
# COMPLAINTS & REPORTS SYSTEM
# =========================================================================
def create_complaint(
    db: Session,
    reporter_id: int,
    reported_user_id: Optional[int],
    donation_id: Optional[int],
    title: str,
    description: str
) -> ReportComplaint:
    complaint = ReportComplaint(
        reporter_id=reporter_id,
        reported_user_id=reported_user_id,
        donation_id=donation_id,
        title=title,
        description=description,
        status="pending"
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    
    # Notify Admin
    admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
    for admin in admins:
        create_notification(
            db,
            user_id=admin.id,
            title="New Complaint Filed",
            message=f"A complaint titled '{title}' has been filed and is pending investigation.",
            notification_type=NotificationType.ALERT
        )
        
    create_audit_log(
        db,
        actor_id=reporter_id,
        action="complaint_create",
        target_table="reports_complaints",
        target_id=complaint.id
    )
    return complaint

def resolve_complaint(db: Session, complaint_id: int, notes: str, status_choice: str, admin_id: int) -> ReportComplaint:
    complaint = db.query(ReportComplaint).filter(ReportComplaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    complaint.status = status_choice
    complaint.resolution_notes = notes
    db.commit()
    db.refresh(complaint)
    
    # Notify reporter
    create_notification(
        db,
        user_id=complaint.reporter_id,
        title="Complaint Status Update",
        message=f"Your complaint '{complaint.title}' has been marked as {status_choice}. Resolution: {notes}",
        notification_type=NotificationType.SYSTEM
    )
    
    create_audit_log(
        db,
        actor_id=admin_id,
        action=f"complaint_resolve_{status_choice}",
        target_table="reports_complaints",
        target_id=complaint.id
    )
    return complaint
