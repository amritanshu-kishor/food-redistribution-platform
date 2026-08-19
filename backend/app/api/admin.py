from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_admin
from app.crud.crud import (
    verify_organization, update_user_status, resolve_complaint, create_audit_log,
    calculate_remaining_quantity
)
from app.models.models import (
    User, UserStatus, UserRole, Organization, OrgVerificationStatus, OrganizationDocument,
    Donation, DonationStatus, DonationAllocation, AllocationStatus, AuditLog, ReportComplaint
)
from app.schemas.schemas import (
    UserOut, OrganizationOut, DocumentOut, AuditLogOut, ComplaintOut, ComplaintResolve
)
from app.utils.reports import generate_csv_report, generate_pdf_report

router = APIRouter()

@router.get("/users", response_model=List[UserOut])
def list_users(
    role: Optional[UserRole] = Query(None),
    status: Optional[UserStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all platform users (Admin only)."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    return query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

@router.put("/users/{user_id}/status", response_model=UserOut)
def change_user_status(
    user_id: int,
    status_choice: UserStatus,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Suspend or reactivate a user account (Admin only)."""
    return update_user_status(db, user_id, status_choice, current_admin.id)

@router.get("/organizations", response_model=List[OrganizationOut])
def list_organizations(
    verification_status: Optional[OrgVerificationStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List all registered organizations (Admin only)."""
    query = db.query(Organization)
    if verification_status:
        query = query.filter(Organization.verification_status == verification_status)
    return query.order_by(Organization.created_at.desc()).offset(skip).limit(limit).all()

@router.put("/organizations/{org_id}/verify", response_model=OrganizationOut)
def verify_org(
    org_id: int,
    status_choice: OrgVerificationStatus,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Approve or reject organization verification status (Admin only)."""
    return verify_organization(db, org_id, status_choice, current_admin.id)

@router.get("/documents", response_model=List[DocumentOut])
def list_uploaded_documents(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List organization documents uploaded for verification (Admin only)."""
    return db.query(OrganizationDocument).order_by(OrganizationDocument.uploaded_at.desc()).all()

@router.get("/audit-logs", response_model=List[AuditLogOut])
def list_audit_logs(
    action: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Retrieve system audit logs (Admin only)."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    logs = query.order_by(AuditLog.timestamp.desc()).offset(skip).limit(limit).all()
    # Populate user name
    for log in logs:
        if log.actor:
            log.actor_name = log.actor.full_name
    return logs

@router.get("/complaints", response_model=List[ComplaintOut])
def list_complaints(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """List reported complaints and support issues (Admin only)."""
    query = db.query(ReportComplaint)
    if status:
        query = query.filter(ReportComplaint.status == status)
    complaints = query.order_by(ReportComplaint.created_at.desc()).all()
    # Populate helper fields
    for c in complaints:
        c.reporter_name = c.reporter.full_name
        if c.reported_user:
            c.reported_user_name = c.reported_user.full_name
        if c.donation:
            c.donation_title = c.donation.title
    return complaints

@router.put("/complaints/{complaint_id}/resolve", response_model=ComplaintOut)
def resolve_admin_complaint(
    complaint_id: int,
    req: ComplaintResolve,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Resolve or dismiss a pending complaint (Admin only)."""
    complaint = resolve_complaint(db, complaint_id, req.resolution_notes, req.status, current_admin.id)
    complaint.reporter_name = complaint.reporter.full_name
    if complaint.reported_user:
        complaint.reported_user_name = complaint.reported_user.full_name
    if complaint.donation:
        complaint.donation_title = complaint.donation.title
    return complaint

@router.get("/dashboard/metrics")
def get_dashboard_metrics(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Retrieve aggregated platform metrics based on actual database contents."""
    total_donations = db.query(Donation).count()
    total_redistributed = db.query(func.sum(DonationAllocation.allocated_quantity)).filter(
        DonationAllocation.status == AllocationStatus.COMPLETED
    ).scalar() or 0.0
    
    active_listings = db.query(Donation).filter(Donation.status == DonationStatus.AVAILABLE).count()
    completed_listings = db.query(Donation).filter(Donation.status == DonationStatus.COMPLETED).count()
    expired_listings = db.query(Donation).filter(Donation.status == DonationStatus.EXPIRED).count()
    
    restaurants_count = db.query(User).filter(User.role == UserRole.RESTAURANT).count()
    ngos_count = db.query(User).filter(User.role == UserRole.NGO).count()
    pending_orgs = db.query(Organization).filter(Organization.verification_status == OrgVerificationStatus.PENDING).count()
    
    # Category Distribution
    category_counts = db.query(Donation.category, func.count(Donation.id)).group_by(Donation.category).all()
    categories_data = [{"category": row[0], "count": row[1]} for row in category_counts]
    
    # Activity over time (Grouped by date)
    daily_donations = db.query(
        func.date(Donation.created_at),
        func.count(Donation.id)
    ).group_by(func.date(Donation.created_at)).order_by(func.date(Donation.created_at).asc()).all()
    
    activity_timeline = [{"date": str(row[0]), "donations": row[1]} for row in daily_donations]
    
    return {
        "total_donations": total_donations,
        "total_redistributed": total_redistributed,
        "active_listings": active_listings,
        "completed_listings": completed_listings,
        "expired_listings": expired_listings,
        "restaurants_count": restaurants_count,
        "ngos_count": ngos_count,
        "pending_orgs": pending_orgs,
        "categories_distribution": categories_data,
        "activity_timeline": activity_timeline
    }

@router.get("/reports/download")
def download_reports(
    report_type: str = Query("donations", description="Options: 'donations', 'users', 'audit'"),
    report_format: str = Query("pdf", description="Options: 'pdf', 'csv'"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Generate and download a CSV/PDF platform report (Admin only)."""
    now_str = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S")
    
    if report_type == "donations":
        donations = db.query(Donation).all()
        # Compile list of dicts
        items = []
        for d in donations:
            items.append({
                "id": d.id,
                "donor": d.donor.name,
                "title": d.title,
                "category": d.category,
                "quantity": f"{d.quantity} {d.unit}",
                "status": d.status.value,
                "expires_at": d.expires_at
            })
        
        headers = ["ID", "Donor", "Title", "Category", "Quantity", "Status", "Expires At"]
        keys = ["id", "donor", "title", "category", "quantity", "status", "expires_at"]
        title = "Food Redistribution - Donations Impact Report"
        filename = f"donations_report_{now_str}"
        
        metrics = {
            "Total Listings": len(donations),
            "Available Listings": sum(1 for d in donations if d.status == DonationStatus.AVAILABLE),
            "Completed Listings": sum(1 for d in donations if d.status == DonationStatus.COMPLETED),
            "Expired Listings": sum(1 for d in donations if d.status == DonationStatus.EXPIRED)
        }
        
    elif report_type == "users":
        users = db.query(User).all()
        items = []
        for u in users:
            org_name = u.organization.name if u.organization else "-"
            items.append({
                "id": u.id,
                "email": u.email,
                "name": u.full_name,
                "role": u.role.value,
                "status": u.status.value,
                "organization": org_name,
                "created_at": u.created_at
            })
            
        headers = ["ID", "Email", "Full Name", "Role", "Status", "Organization", "Registered At"]
        keys = ["id", "email", "name", "role", "status", "organization", "created_at"]
        title = "Food Redistribution - Platform Users Audit"
        filename = f"users_report_{now_str}"
        
        metrics = {
            "Total Users": len(users),
            "Active Accounts": sum(1 for u in users if u.status == UserStatus.ACTIVE),
            "Pending Review": sum(1 for u in users if u.status == UserStatus.PENDING),
            "Suspended Users": sum(1 for u in users if u.status == UserStatus.SUSPENDED)
        }
        
    elif report_type == "audit":
        logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(200).all()
        items = []
        for l in logs:
            items.append({
                "id": l.id,
                "actor": l.actor.full_name if l.actor else "System",
                "action": l.action,
                "table": l.target_table,
                "target_id": l.target_id or "-",
                "timestamp": l.timestamp
            })
            
        headers = ["ID", "Actor Name", "Action Logged", "Target Table", "Target ID", "Logged At"]
        keys = ["id", "actor", "action", "table", "target_id", "timestamp"]
        title = "Food Redistribution - System Security Audit Log"
        filename = f"security_audit_{now_str}"
        
        metrics = {
            "Audited Logs": len(logs),
            "System Actions": sum(1 for l in logs if "auto" in l.action or "system" in l.action),
            "User Mutations": sum(1 for l in logs if "register" in l.action or "login" in l.action or "create" in l.action)
        }
        
    else:
        raise HTTPException(status_code=400, detail="Invalid report_type")
        
    # Render format
    if report_format == "csv":
        csv_str = generate_csv_report(items, keys)
        return Response(
            content=csv_str,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
        )
    elif report_format == "pdf":
        pdf_bytes = generate_pdf_report(title, metrics, items, headers, keys)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}.pdf"}
        )
        
    raise HTTPException(status_code=400, detail="Invalid report_format")
