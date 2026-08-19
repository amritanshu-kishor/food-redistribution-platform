from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_ngo, get_current_restaurant
from app.crud.crud import (
    create_allocation, accept_allocation, reject_allocation, calculate_remaining_quantity
)
from app.models.models import DonationAllocation, User, UserRole, Donation, AllocationStatus
from app.schemas.schemas import AllocationCreate, AllocationOut

router = APIRouter()

@router.post("/", response_model=AllocationOut, status_code=status.HTTP_201_CREATED)
def claim_food_allocation(
    alloc_in: AllocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_ngo)
):
    """Claim a quantity of an available donation (NGO only)."""
    return create_allocation(db, alloc_in, current_user.organization.id)

@router.post("/{allocation_id}/accept", response_model=AllocationOut)
def approve_claim(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_restaurant)
):
    """Approve a pending NGO claim request (Restaurant donor only)."""
    return accept_allocation(db, allocation_id, current_user.id)

@router.post("/{allocation_id}/reject", response_model=AllocationOut)
def decline_claim(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_restaurant)
):
    """Decline a pending NGO claim request (Restaurant donor only)."""
    return reject_allocation(db, allocation_id, current_user.id)

@router.get("/my/claims", response_model=List[AllocationOut])
def get_my_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_ngo)
):
    """Retrieve claims history and active requests for the logged-in NGO."""
    allocations = db.query(DonationAllocation).filter(
        DonationAllocation.receiver_id == current_user.organization.id
    ).order_by(DonationAllocation.created_at.desc()).all()
    
    # Pre-populate helper fields
    for a in allocations:
        a.receiver_name = a.receiver.name
        a.donation.donor_name = a.donation.donor.name
    return allocations

@router.get("/my/incoming", response_model=List[AllocationOut])
def get_incoming_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_restaurant)
):
    """Retrieve claims requested by NGOs on the Restaurant's donations."""
    allocations = db.query(DonationAllocation).join(Donation).filter(
        Donation.donor_id == current_user.organization.id
    ).order_by(DonationAllocation.created_at.desc()).all()
    
    for a in allocations:
        a.receiver_name = a.receiver.name
        a.donation.donor_name = a.donation.donor.name
    return allocations

@router.get("/{allocation_id}", response_model=AllocationOut)
def get_allocation_details(
    allocation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve details for a single claim allocation."""
    allocation = db.query(DonationAllocation).filter(DonationAllocation.id == allocation_id).first()
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
        
    # Check permissions
    is_admin = current_user.role == UserRole.ADMIN
    is_involved = current_user.organization and current_user.organization.id in [
        allocation.receiver_id,
        allocation.donation.donor_id
    ]
    if not is_admin and not is_involved:
        raise HTTPException(status_code=403, detail="Not authorized to view this allocation")
        
    allocation.receiver_name = allocation.receiver.name
    allocation.donation.donor_name = allocation.donation.donor.name
    return allocation
