import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models.models import (
    User, UserRole, UserStatus, Organization, OrgVerificationStatus,
    Donation, DonationStatus, DonationAllocation, AllocationStatus,
    QRVerificationType, QRVerificationEvent, AuditLog
)

# SQLite Test Database Setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_food_redist.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    db = TestingSessionLocal(bind=connection)
    
    yield db
    
    db.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

# =========================================================================
# HELPER SIGNUP & LOGIN FLOWS
# =========================================================================
def register_user(client: TestClient, email: str, role: str, name: str) -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "full_name": name,
            "role": role,
            "organization": {
                "name": f"{name} Org",
                "address": "123 Main St",
                "description": "Details about org"
            }
        }
    )
    assert resp.status_code == 201
    return resp.json()

def get_headers(client: TestClient, email: str) -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": "Password123!"}
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

# =========================================================================
# INTEGRATION TESTING LCYCLE
# =========================================================================

def test_food_share_platform_integration(client: TestClient, db_session):
    """Run an end-to-end integration test validating the entire platform lifecycle."""
    
    # -------------------------------------------------------------
    # 1. AUTHENTICATION & APPROVALS
    # -------------------------------------------------------------
    # Register Restaurant, NGO 1, NGO 2, and Admin
    rest_info = register_user(client, "rest@diner.com", "restaurant", "Happy Diner")
    ngo1_info = register_user(client, "ngo1@foodbank.org", "ngo", "Harvest NGO")
    ngo2_info = register_user(client, "ngo2@foodbank.org", "ngo", "Help NGO")
    
    # Admin registers
    admin_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@share.com",
            "password": "Password123!",
            "full_name": "System Admin",
            "role": "admin"
        }
    )
    assert admin_resp.status_code == 201
    admin_headers = get_headers(client, "admin@share.com")
    
    # Verify restaurant can log in while pending, but cannot create a donation
    pending_headers = get_headers(client, "rest@diner.com")
    post_fail = client.post(
        "/api/v1/donations/",
        json={
            "title": "Delicious Stew",
            "description": "Vegetable stew prepared today",
            "category": "Prepared Meals",
            "quantity": 10,
            "unit": "portions",
            "prepared_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
            "pickup_start": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "pickup_end": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
            "address": "123 Diner St"
        },
        headers=pending_headers
    )
    assert post_fail.status_code == 403
    assert "status" in post_fail.json()["detail"].lower()
    
    # Admin approves users
    db_rest_org = db_session.query(Organization).filter(Organization.user_id == rest_info["id"]).first()
    db_ngo1_org = db_session.query(Organization).filter(Organization.user_id == ngo1_info["id"]).first()
    db_ngo2_org = db_session.query(Organization).filter(Organization.user_id == ngo2_info["id"]).first()
    
    client.put(f"/api/v1/admin/organizations/{db_rest_org.id}/verify?status_choice=approved", headers=admin_headers)
    client.put(f"/api/v1/admin/organizations/{db_ngo1_org.id}/verify?status_choice=approved", headers=admin_headers)
    client.put(f"/api/v1/admin/organizations/{db_ngo2_org.id}/verify?status_choice=approved", headers=admin_headers)
    
    # Logins should now succeed
    rest_headers = get_headers(client, "rest@diner.com")
    ngo1_headers = get_headers(client, "ngo1@foodbank.org")
    ngo2_headers = get_headers(client, "ngo2@foodbank.org")
    
    # -------------------------------------------------------------
    # 2. DONATION CRUD & STATUS TRANSITIONS
    # -------------------------------------------------------------
    prepared_time = datetime.utcnow() + timedelta(hours=1)
    expiry_time = datetime.utcnow() + timedelta(hours=8)
    
    # Create Donation (DRAFT by default)
    post_resp = client.post(
        "/api/v1/donations/",
        json={
            "title": "Delicious Stew",
            "description": "Vegetable stew prepared today",
            "category": "Prepared Meals",
            "quantity": 10,
            "unit": "portions",
            "prepared_at": prepared_time.isoformat(),
            "expires_at": expiry_time.isoformat(),
            "pickup_start": prepared_time.isoformat(),
            "pickup_end": expiry_time.isoformat(),
            "address": "123 Diner St"
        },
        headers=rest_headers
    )
    assert post_resp.status_code == 201
    donation_id = post_resp.json()["id"]
    assert post_resp.json()["status"] == "DRAFT"
    
    # Publish Donation (DRAFT -> AVAILABLE)
    pub_resp = client.put(
        f"/api/v1/donations/{donation_id}",
        json={"status": "AVAILABLE"},
        headers=rest_headers
    )
    assert pub_resp.status_code == 200
    assert pub_resp.json()["status"] == "AVAILABLE"
    
    # Invalid Transition: AVAILABLE -> DRAFT (should fail)
    invalid_resp = client.put(
        f"/api/v1/donations/{donation_id}",
        json={"status": "DRAFT"},
        headers=rest_headers
    )
    assert invalid_resp.status_code == 400
    assert "Invalid donation status transition" in invalid_resp.json()["detail"]
    
    # -------------------------------------------------------------
    # 3. PARTIAL ALLOCATIONS & RACE-CONDITIONS
    # -------------------------------------------------------------
    # NGO 1 claims 6 portions -> success
    claim1 = client.post(
        "/api/v1/allocations/",
        json={"donation_id": donation_id, "requested_quantity": 6},
        headers=ngo1_headers
    )
    assert claim1.status_code == 201
    alloc1_id = claim1.json()["id"]
    
    # NGO 2 claims 5 portions -> fails because remaining available is 4
    claim2_fail = client.post(
        "/api/v1/allocations/",
        json={"donation_id": donation_id, "requested_quantity": 5},
        headers=ngo2_headers
    )
    assert claim2_fail.status_code == 400
    assert "exceeds remaining available quantity" in claim2_fail.json()["detail"]
    
    # NGO 2 claims 4 portions -> success
    claim2_ok = client.post(
        "/api/v1/allocations/",
        json={"donation_id": donation_id, "requested_quantity": 4},
        headers=ngo2_headers
    )
    assert claim2_ok.status_code == 201
    alloc2_id = claim2_ok.json()["id"]
    
    # Approve claims (Locking quantity)
    accept1 = client.post(f"/api/v1/allocations/{alloc1_id}/accept", headers=rest_headers)
    assert accept1.status_code == 200
    assert accept1.json()["status"] == "ACCEPTED"
    qr_token1 = accept1.json()["qr_token"]
    assert qr_token1 is not None
    
    accept2 = client.post(f"/api/v1/allocations/{alloc2_id}/accept", headers=rest_headers)
    assert accept2.status_code == 200
    assert accept2.json()["status"] == "ACCEPTED"
    qr_token2 = accept2.json()["qr_token"]
    
    # Donation status should change to ACCEPTED since all 10 portions are allocated
    db_donation = db_session.query(Donation).filter(Donation.id == donation_id).first()
    assert db_donation.status == DonationStatus.ACCEPTED
    
    # -------------------------------------------------------------
    # 4. QR VERIFICATION CODES
    # -------------------------------------------------------------
    # Restaurant scans NGO 1's QR code to confirm pickup
    pickup_resp = client.post(
        "/api/v1/qr/verify",
        json={"scanned_code": qr_token1, "event_type": "PICKUP"},
        headers=rest_headers
    )
    assert pickup_resp.status_code == 200
    assert pickup_resp.json()["status"] == "SUCCESS"
    
    # Verify allocation status
    db_alloc1 = db_session.query(DonationAllocation).filter(DonationAllocation.id == alloc1_id).first()
    assert db_alloc1.status == AllocationStatus.PICKED_UP
    
    # Donation goes to PICKUP_PENDING (since allocation 2 is not picked up yet)
    db_session.refresh(db_donation)
    assert db_donation.status == DonationStatus.PICKUP_PENDING
    
    # NGO 1 completes distribution
    complete_resp = client.post(
        "/api/v1/qr/verify",
        json={"scanned_code": qr_token1, "event_type": "COMPLETION"},
        headers=ngo1_headers
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "SUCCESS"
    
    # Verify allocation status is completed
    db_session.refresh(db_alloc1)
    assert db_alloc1.status == AllocationStatus.COMPLETED
    
    # -------------------------------------------------------------
    # 5. PERMISSIONS & UNAUTHORIZED ACCESS
    # -------------------------------------------------------------
    # NGO 2 tries to accept NGO 1's claim -> 403 Forbidden
    accept_fail = client.post(f"/api/v1/allocations/{alloc1_id}/accept", headers=ngo2_headers)
    assert accept_fail.status_code == 403
    
    # NGO trying to create a donation should fail
    post_fail = client.post(
        "/api/v1/donations/",
        json={
            "title": "Illegal food",
            "category": "Prepared Meals",
            "quantity": 10,
            "unit": "portions",
            "prepared_at": prepared_time.isoformat(),
            "expires_at": expiry_time.isoformat(),
            "pickup_start": prepared_time.isoformat(),
            "pickup_end": expiry_time.isoformat(),
            "address": "123 Diner St"
        },
        headers=ngo1_headers
    )
    assert post_fail.status_code == 403
    
    # -------------------------------------------------------------
    # 6. AUDIT LOGS & REPORTS
    # -------------------------------------------------------------
    # Admin checks audit logs
    logs_resp = client.get("/api/v1/admin/audit-logs", headers=admin_headers)
    assert logs_resp.status_code == 200
    assert len(logs_resp.json()) > 0
    
    # Verify some recorded actions
    actions = [log["action"] for log in logs_resp.json()]
    assert "user_register" in actions
    assert "donation_create" in actions
    
    # Admin downloads PDF report
    pdf_resp = client.get("/api/v1/admin/reports/download?report_type=donations&report_format=pdf", headers=admin_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    
    # Admin downloads CSV report
    csv_resp = client.get("/api/v1/admin/reports/download?report_type=donations&report_format=csv", headers=admin_headers)
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp.headers["content-type"]
