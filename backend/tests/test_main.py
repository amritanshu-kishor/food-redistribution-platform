import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash
from app.models.models import (
    User, UserRole, UserStatus, Organization, OrgVerificationStatus,
    Donation, DonationStatus, DonationAllocation, AllocationStatus,
    QRVerificationType, QRVerificationEvent, AuditLog, AuthToken
)

# SQLite Test Database Setup
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
@event.listens_for(engine, "connect")
def enforce_foreign_keys(connection, _record):
    connection.execute("PRAGMA foreign_keys=ON")
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
    # Register Restaurant and NGOs. The administrator is bootstrapped on the
    # server side and cannot be created through public registration.
    rest_info = register_user(client, "rest@diner.com", "restaurant", "Happy Diner")
    ngo1_info = register_user(client, "ngo1@foodbank.org", "ngo", "Harvest NGO")
    ngo2_info = register_user(client, "ngo2@foodbank.org", "ngo", "Help NGO")
    
    admin_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin@share.com",
            "password": "Password123!",
            "full_name": "System Admin",
            "role": "admin"
        }
    )
    assert admin_resp.status_code == 422
    admin_user = User(
        email="admin@share.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="System Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(admin_user)
    db_session.commit()
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


def test_public_admin_registration_is_rejected(client: TestClient):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "attacker@example.com",
            "password": "Password123!",
            "full_name": "Attacker",
            "role": "admin",
            "organization": {
                "name": "Untrusted Admin Org",
                "address": "1 Test Street",
            },
        },
    )
    assert response.status_code == 422


def test_refresh_tokens_are_hashed_and_revoked_on_logout(client: TestClient, db_session):
    user = User(
        email="secure-user@example.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Secure User",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": "Password123!"},
    )
    assert login_response.status_code == 200
    tokens = login_response.json()
    stored = db_session.query(AuthToken).filter(AuthToken.user_id == user.id).first()
    assert stored is not None
    assert stored.token != tokens["refresh_token"]
    assert len(stored.token) == 64

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    logout_response = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=headers,
    )
    assert logout_response.status_code == 200
    assert client.get("/api/v1/users/profile", headers=headers).status_code == 401
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_response.status_code == 401


def test_pending_users_can_refresh_without_access_to_partner_operations(client: TestClient, db_session):
    user = User(
        email="pending-user@example.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Pending User",
        role=UserRole.RESTAURANT,
        status=UserStatus.PENDING,
    )
    db_session.add(user)
    db_session.commit()
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": user.email, "password": "Password123!"},
    )
    assert login_response.status_code == 200
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_response.json()["refresh_token"]},
    )
    assert refresh_response.status_code == 200


def test_admin_account_cannot_be_suspended(client: TestClient, db_session):
    admin = User(
        email="only-admin@example.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="Only Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(admin)
    db_session.commit()
    headers = get_headers(client, admin.email)

    response = client.put(
        f"/api/v1/admin/users/{admin.id}/status?status_choice=suspended",
        headers=headers,
    )
    assert response.status_code == 400


def test_invalid_qr_does_not_create_orphan_event(client: TestClient, db_session):
    admin = User(
        email="qr-admin@example.com",
        hashed_password=get_password_hash("Password123!"),
        full_name="QR Admin",
        role=UserRole.ADMIN,
        status=UserStatus.ACTIVE,
    )
    db_session.add(admin)
    db_session.commit()
    headers = get_headers(client, admin.email)

    response = client.post(
        "/api/v1/qr/verify",
        json={"scanned_code": "not-a-real-qr-token", "event_type": "PICKUP"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "INVALID"
    assert db_session.query(QRVerificationEvent).count() == 0


@pytest.fixture
def partners(client, db_session):
    result = {}
    for key, role in (("donor", UserRole.RESTAURANT), ("other", UserRole.RESTAURANT), ("ngo", UserRole.NGO), ("ngo2", UserRole.NGO)):
        user = User(email=f"{key}@example.org", hashed_password=get_password_hash("Password123!"),
                    full_name=key.title(), role=role, status=UserStatus.ACTIVE)
        user.organization = Organization(name=f"{key} organization", address="123 Test Street",
                                         is_verified=True, verification_status=OrgVerificationStatus.APPROVED)
        db_session.add(user)
        db_session.commit()
        result[key] = (user, get_headers(client, user.email))
    return result


def published_food(client, partners, quantity=10):
    now = datetime.now(timezone.utc)
    response = client.post("/api/v1/donations/", headers=partners["donor"][1], json={
        "title": "Surplus soup", "category": "Prepared Meals", "quantity": quantity,
        "unit": "portions", "address": "123 Test Street",
        "prepared_at": (now - timedelta(hours=1)).isoformat(),
        "expires_at": (now + timedelta(hours=4)).isoformat(),
        "pickup_start": (now - timedelta(minutes=30)).isoformat(),
        "pickup_end": (now + timedelta(hours=3)).isoformat(),
    })
    assert response.status_code == 201, response.text
    identifier = response.json()["id"]
    response = client.put(f"/api/v1/donations/{identifier}", headers=partners["donor"][1], json={"status": "AVAILABLE"})
    assert response.status_code == 200, response.text
    return identifier


def accepted_claim(client, partners, food, quantity=10):
    claim = client.post("/api/v1/allocations/", headers=partners["ngo"][1], json={"donation_id": food, "requested_quantity": quantity})
    assert claim.status_code == 201, claim.text
    response = client.post(f"/api/v1/allocations/{claim.json()['id']}/accept", headers=partners["donor"][1])
    assert response.status_code == 200, response.text
    return response.json()


def test_restaurant_dashboard_incoming_claims(client, partners):
    food = published_food(client, partners)
    claim = accepted_claim(client, partners, food)
    response = client.get("/api/v1/allocations/my/incoming", headers=partners["donor"][1])
    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [claim["id"]]
    assert client.get("/api/v1/allocations/my/incoming", headers=partners["other"][1]).json() == []


def test_utc_partial_schedule_update(client, partners):
    food = published_food(client, partners)
    response = client.put(f"/api/v1/donations/{food}", headers=partners["donor"][1], json={
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=5)).isoformat(),
    })
    assert response.status_code == 200


def test_expired_claim_cannot_be_accepted(client, partners, db_session):
    food = published_food(client, partners)
    claim = client.post("/api/v1/allocations/", headers=partners["ngo"][1], json={"donation_id": food, "requested_quantity": 10}).json()
    donation = db_session.get(Donation, food)
    donation.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    assert client.post(f"/api/v1/allocations/{claim['id']}/accept", headers=partners["donor"][1]).status_code == 400


def test_pickup_requires_donor_and_completion_requires_receiver(client, partners):
    food = published_food(client, partners)
    claim = accepted_claim(client, partners, food)
    pickup = {"scanned_code": claim["qr_token"], "event_type": "PICKUP"}
    complete = {**pickup, "event_type": "COMPLETION"}
    assert client.post("/api/v1/qr/verify", headers=partners["ngo"][1], json=pickup).status_code == 403
    assert client.post("/api/v1/qr/verify", headers=partners["other"][1], json=pickup).status_code == 403
    assert client.post("/api/v1/qr/verify", headers=partners["donor"][1], json=pickup).json()["status"] == "SUCCESS"
    assert client.post("/api/v1/qr/verify", headers=partners["donor"][1], json=complete).status_code == 403
    assert client.post("/api/v1/qr/verify", headers=partners["ngo"][1], json=complete).json()["status"] == "SUCCESS"
    assert client.get(f"/api/v1/donations/{food}", headers=partners["donor"][1]).json()["status"] == "COMPLETED"


def test_partial_handover_preserves_remaining_food(client, partners):
    food = published_food(client, partners)
    claim = accepted_claim(client, partners, food, quantity=4)
    for actor, event_type in (("donor", "PICKUP"), ("ngo", "COMPLETION")):
        response = client.post("/api/v1/qr/verify", headers=partners[actor][1], json={"scanned_code": claim["qr_token"], "event_type": event_type})
        assert response.json()["status"] == "SUCCESS"
    response = client.get("/api/v1/donations/browse", headers=partners["ngo2"][1])
    listing = next(item for item in response.json() if item["id"] == food)
    assert listing["available_quantity"] == 6
    assert client.post("/api/v1/allocations/", headers=partners["ngo2"][1], json={"donation_id": food, "requested_quantity": 6}).status_code == 201


def test_pending_cancellation_cancels_claim_and_prevents_accept(client, partners):
    food = published_food(client, partners)
    claim = client.post("/api/v1/allocations/", headers=partners["ngo"][1], json={"donation_id": food, "requested_quantity": 5}).json()
    assert client.put(f"/api/v1/donations/{food}", headers=partners["donor"][1], json={"status": "CANCELLED"}).status_code == 200
    assert client.get(f"/api/v1/allocations/{claim['id']}", headers=partners["ngo"][1]).json()["status"] == "CANCELLED"
    assert client.post(f"/api/v1/allocations/{claim['id']}/accept", headers=partners["donor"][1]).status_code == 400


def test_unicode_password_invalid_is_safe_422(client):
    response = client.post("/api/v1/auth/register", json={"email": "unicode@example.org", "full_name": "Unicode User", "role": "ngo", "password": "🍜" * 30, "organization": {"name": "Soup Kitchen", "address": "123 Test Street"}})
    assert response.status_code == 422
    assert "🍜" not in response.text


def test_unknown_login_placeholder_is_unauthorized(client):
    response = client.post("/api/v1/auth/login", data={"username": "missing@example.org", "password": "invalid-login-placeholder"})
    assert response.status_code == 401


def test_suspended_existing_session_cannot_upload_or_update(client, partners, db_session):
    user, headers = partners["ngo"]
    user.status = UserStatus.SUSPENDED
    db_session.commit()
    assert client.put("/api/v1/users/profile", headers=headers, json={"full_name": "Changed Name"}).status_code == 403


def test_untrusted_profile_fields_rejected(client, partners):
    response = client.put("/api/v1/users/profile", headers=partners["ngo"][1], json={"role": "admin", "status": "active"})
    assert response.status_code == 422


def test_missing_production_secrets_rejected():
    from app.core.config import Settings
    with pytest.raises(ValueError):
        Settings(_env_file=None, ENV="production", JWT_SECRET_KEY="", JWT_REFRESH_SECRET_KEY="", CORS_ORIGINS="https://food.example.org")


def test_create_normalizes_mixed_timezone_schedule(client, partners, db_session):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    offset = timezone(timedelta(hours=5, minutes=30))
    response = client.post("/api/v1/donations/", headers=partners["donor"][1], json={
        "title": "Timezone soup", "category": "Prepared Meals", "quantity": 10,
        "unit": "portions", "address": "123 Test Street",
        "prepared_at": (now - timedelta(hours=1)).replace(tzinfo=None).isoformat(),
        "expires_at": (now + timedelta(hours=4)).astimezone(offset).isoformat(),
        "pickup_start": now.isoformat(),
        "pickup_end": (now + timedelta(hours=3)).astimezone(offset).isoformat(),
    })
    assert response.status_code == 201, response.text
    donation = db_session.get(Donation, response.json()["id"])
    assert donation.expires_at == (now + timedelta(hours=4)).replace(tzinfo=None)
    assert response.json()["expires_at"].endswith("Z")


def test_browse_subtracts_pending_reservations(client, partners):
    food = published_food(client, partners)
    response = client.post("/api/v1/allocations/", headers=partners["ngo"][1], json={
        "donation_id": food, "requested_quantity": 6,
    })
    assert response.status_code == 201
    listing = next(item for item in client.get("/api/v1/donations/browse", headers=partners["ngo2"][1]).json() if item["id"] == food)
    assert listing["available_quantity"] == 4
    assert client.post("/api/v1/allocations/", headers=partners["ngo2"][1], json={
        "donation_id": food, "requested_quantity": 4,
    }).status_code == 201
    assert client.get("/api/v1/donations/browse", headers=partners["ngo2"][1]).json() == []


def test_rejection_releases_last_pending_reservation(client, partners):
    food = published_food(client, partners)
    claim = client.post("/api/v1/allocations/", headers=partners["ngo"][1], json={
        "donation_id": food, "requested_quantity": 10,
    }).json()
    assert client.post(f"/api/v1/allocations/{claim['id']}/reject", headers=partners["donor"][1]).status_code == 200
    donation = client.get(f"/api/v1/donations/{food}", headers=partners["donor"][1]).json()
    assert donation["status"] == "AVAILABLE"
    assert donation["available_quantity"] == 10


def test_partial_pickup_keeps_unreserved_food_browsable(client, partners):
    food = published_food(client, partners)
    claim = accepted_claim(client, partners, food, quantity=4)
    assert client.post("/api/v1/allocations/", headers=partners["ngo2"][1], json={
        "donation_id": food, "requested_quantity": 2,
    }).status_code == 201
    assert client.post("/api/v1/qr/verify", headers=partners["donor"][1], json={
        "scanned_code": claim["qr_token"], "event_type": "PICKUP",
    }).json()["status"] == "SUCCESS"
    listings = client.get("/api/v1/donations/browse", headers=partners["ngo2"][1]).json()
    assert len(listings) == 1
    assert listings[0]["available_quantity"] == 4


def test_expired_food_cannot_be_picked_up_without_browse(client, partners, db_session):
    food = published_food(client, partners)
    claim = accepted_claim(client, partners, food)
    db_session.get(Donation, food).expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    response = client.post("/api/v1/qr/verify", headers=partners["donor"][1], json={
        "scanned_code": claim["qr_token"], "event_type": "PICKUP",
    })
    assert response.status_code == 200
    assert response.json()["status"] == "FAILED"
    assert db_session.get(DonationAllocation, claim["id"]).status != AllocationStatus.PICKED_UP


def test_completed_claim_freezes_quantity_and_unit(client, partners):
    food = published_food(client, partners)
    claim = accepted_claim(client, partners, food, quantity=4)
    for actor, event_type in (("donor", "PICKUP"), ("ngo", "COMPLETION")):
        assert client.post("/api/v1/qr/verify", headers=partners[actor][1], json={
            "scanned_code": claim["qr_token"], "event_type": event_type,
        }).json()["status"] == "SUCCESS"
    for mutation in ({"quantity": 2}, {"unit": "kg"}):
        assert client.put(f"/api/v1/donations/{food}", headers=partners["donor"][1], json=mutation).status_code == 400


def test_password_reset_is_private_single_use_and_revokes_other_resets(client, partners, monkeypatch):
    import re
    from app.api import auth
    messages = []
    monkeypatch.setattr(auth, "send_email", lambda _to, _subject, body: messages.append(body))
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "unknown@example.org"})
    for _ in range(2):
        known = client.post("/api/v1/auth/forgot-password", json={"email": partners["ngo"][0].email})
        assert known.json() == unknown.json()
    tokens = [re.search(r"token=([a-f0-9]+)", body).group(1) for body in messages]
    payload = {"token": tokens[-1], "new_password": "NewPassword123!"}
    assert client.post("/api/v1/auth/reset-password", json=payload).status_code == 200
    assert client.get("/api/v1/users/profile", headers=partners["ngo"][1]).status_code == 401
    for token in tokens:
        assert client.post("/api/v1/auth/reset-password", json={**payload, "token": token}).status_code == 400
    assert client.post("/api/v1/auth/login", data={"username": partners["ngo"][0].email, "password": "NewPassword123!"}).status_code == 200
