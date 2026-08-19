import math
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.deps import get_current_active_user, get_current_restaurant
from app.crud.crud import (
    create_donation, update_donation, auto_expire_donations, calculate_remaining_quantity,
    create_audit_log
)
from app.models.models import Donation, DonationStatus, User, UserRole, Organization
from app.schemas.schemas import DonationCreate, DonationUpdate, DonationOut
from app.utils.storage import save_uploaded_file

router = APIRouter()

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points in km."""
    if None in [lat1, lon1, lat2, lon2]:
        return float('inf')
    R = 6371.0  # Earth's radius in kilometers
    
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

@router.post("/", response_model=DonationOut, status_code=status.HTTP_201_CREATED)
def create_new_donation(
    donation_in: DonationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_restaurant)
):
    """Post a new food donation listing (Restaurant only)."""
    return create_donation(db, donation_in, current_user.organization.id)

@router.put("/{donation_id}", response_model=DonationOut)
def edit_donation(
    donation_id: int,
    donation_in: DonationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update details or status of an existing donation (Restaurant owner or Admin)."""
    return update_donation(db, donation_id, donation_in, current_user.id)

@router.post("/{donation_id}/image", response_model=DonationOut)
def upload_donation_image(
    donation_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_restaurant)
):
    """Upload a food photo for a donation."""
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
        
    if donation.donor_id != current_user.organization.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this donation")
        
    image_url = save_uploaded_file(file, is_image=True)
    donation.image_path = image_url
    db.commit()
    db.refresh(donation)
    
    create_audit_log(
        db,
        actor_id=current_user.id,
        action="donation_upload_image",
        target_table="donations",
        target_id=donation.id
    )
    return donation

@router.get("/my/listings", response_model=List[DonationOut])
def get_my_listings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_restaurant)
):
    """Fetch all listings posted by the logged-in Restaurant."""
    # Process auto-expiry first
    auto_expire_donations(db)
    
    donations = db.query(Donation).filter(Donation.donor_id == current_user.organization.id).all()
    # Add helper fields
    for d in donations:
        d.donor_name = d.donor.name
    return donations

@router.get("/browse", response_model=List[DonationOut])
def browse_donations(
    category: Optional[str] = Query(None),
    min_qty: Optional[float] = Query(None),
    max_distance_km: Optional[float] = Query(None),
    user_lat: Optional[float] = Query(None),
    user_lon: Optional[float] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Browse and filter active donations (AVAILABLE or REQUESTED)."""
    # Enforce background expiry checking on page browse
    auto_expire_donations(db)
    
    # NGO or Admin can browse. If Restaurant, they should use /my/listings, but let's allow read access
    query = db.query(Donation).filter(
        Donation.status.in_([DonationStatus.AVAILABLE, DonationStatus.REQUESTED]),
        Donation.expires_at > datetime.utcnow()
    )
    
    if category:
        query = query.filter(Donation.category == category)
        
    donations = query.order_by(Donation.expires_at.asc()).all()
    
    # Calculate distance and filter/sort
    filtered_donations = []
    for d in donations:
        # Calculate remaining quantity
        rem = calculate_remaining_quantity(d)
        if rem <= 0:
            continue  # Don't show fully allocated donations
            
        d.donor_name = d.donor.name
        
        # Calculate distance
        distance = None
        if None not in [user_lat, user_lon, d.latitude, d.longitude]:
            distance = haversine_distance(user_lat, user_lon, d.latitude, d.longitude)
            
        if max_distance_km is not None:
            if distance is None or distance > max_distance_km:
                continue
                
        if min_qty is not None:
            if rem < min_qty:
                continue
                
        # Cache calculated distance or attribute on object if needed
        filtered_donations.append(d)
        
    # If coordinates are provided, sort results by distance
    if None not in [user_lat, user_lon]:
        filtered_donations.sort(key=lambda x: haversine_distance(user_lat, user_lon, x.latitude, x.longitude))
        
    # Apply pagination manually after sorting
    return filtered_donations[skip : skip + limit]

@router.get("/{donation_id}", response_model=DonationOut)
def get_donation_details(
    donation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Retrieve details for a single donation."""
    donation = db.query(Donation).filter(Donation.id == donation_id).first()
    if not donation:
        raise HTTPException(status_code=404, detail="Donation not found")
    donation.donor_name = donation.donor.name
    return donation
