"""
FoodShare Platform - Database Seed Script
Run from the backend/ directory: python seed.py

Resets demo rows and creates:
  1 admin, 5 restaurants (2 high-volume donors), 5 NGOs (2 high-acceptance),
  2 pending orgs for admin verification, live listings, and completed handovers.
"""
import os
import sys
import secrets
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from app.core.database import Base, engine, SessionLocal
from app.core.security import get_password_hash
from app.models.models import (
    AllocationStatus,
    AuditLog,
    AuthToken,
    Donation,
    DonationAllocation,
    DonationStatus,
    Notification,
    Organization,
    OrganizationDocument,
    OrgVerificationStatus,
    QRVerificationEvent,
    ReportComplaint,
    User,
    UserRole,
    UserStatus,
)

DEMO_PASSWORD = "Demo@1234"
ADMIN_PASSWORD = "Admin@1234"


def wipe_demo(db):
    db.query(QRVerificationEvent).delete()
    db.query(DonationAllocation).delete()
    db.query(Donation).delete()
    db.query(OrganizationDocument).delete()
    db.query(Notification).delete()
    db.query(AuditLog).delete()
    db.query(AuthToken).delete()
    db.query(ReportComplaint).delete()
    db.query(Organization).delete()
    db.query(User).delete()
    db.commit()


def make_user(db, email, full_name, phone, role, status):
    password = ADMIN_PASSWORD if role == UserRole.ADMIN else DEMO_PASSWORD
    user = User(
        email=email,
        hashed_password=get_password_hash(password),
        role=role,
        full_name=full_name,
        phone=phone,
        status=status,
    )
    db.add(user)
    db.flush()
    return user


def make_org(db, user, name, description, address, lat, lon, approved=True, website=None):
    org = Organization(
        user_id=user.id,
        name=name,
        description=description,
        address=address,
        latitude=lat,
        longitude=lon,
        website=website,
        verification_status=OrgVerificationStatus.APPROVED if approved else OrgVerificationStatus.PENDING,
        is_verified=approved,
    )
    db.add(org)
    db.flush()
    return org


def make_donation(db, org, title, desc, category, quantity, unit, hours, address, lat, lon, status, hours_ago=1):
    now = datetime.utcnow()
    prepared = now - timedelta(hours=hours_ago)
    expires = now + timedelta(hours=hours) if status == DonationStatus.AVAILABLE else now - timedelta(hours=2)
    pickup_start = prepared + timedelta(minutes=20)
    pickup_end = expires if status == DonationStatus.AVAILABLE else prepared + timedelta(hours=4)
    donation = Donation(
        donor_id=org.id,
        title=title,
        description=desc,
        category=category,
        quantity=quantity,
        unit=unit,
        prepared_at=prepared,
        expires_at=expires,
        pickup_start=pickup_start,
        pickup_end=pickup_end,
        status=status,
        address=address,
        latitude=lat,
        longitude=lon,
        created_at=prepared,
    )
    db.add(donation)
    db.flush()
    return donation


def make_allocation(db, donation, ngo, qty, status, days_ago=0):
    when = datetime.utcnow() - timedelta(days=days_ago)
    alloc = DonationAllocation(
        donation_id=donation.id,
        receiver_id=ngo.id,
        requested_quantity=qty,
        allocated_quantity=qty,
        status=status,
        qr_token=secrets.token_urlsafe(18),
        created_at=when,
        updated_at=when,
    )
    db.add(alloc)
    db.flush()
    return alloc


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        print("Resetting demo data...")
        wipe_demo(db)

        admin = make_user(
            db,
            "admin@foodshare.io",
            "Platform Administrator",
            "+91-9000000000",
            UserRole.ADMIN,
            UserStatus.ACTIVE,
        )
        print(f"  Admin: {admin.email}")

        restaurants_spec = [
            {
                "email": "contact@spicegarden.com",
                "full_name": "Rajesh Menon",
                "phone": "+91-9811000001",
                "org_name": "Spice Garden Kitchen",
                "org_desc": "Mumbai flagship kitchen — highest donation volume on the platform. Daily thalis, curries, and rice surplus.",
                "address": "14, Church Street, Colaba, Mumbai, Maharashtra 400005",
                "lat": 18.9067,
                "lon": 72.8147,
                "website": "https://spicegarden.example",
            },
            {
                "email": "hello@goldenladle.com",
                "full_name": "Ananya Iyer",
                "phone": "+91-9811000007",
                "org_name": "The Golden Ladle",
                "org_desc": "Pune catering house known for large-batch meals after events. Consistent high-volume donor.",
                "address": "88, FC Road, Shivajinagar, Pune, Maharashtra 411005",
                "lat": 18.5204,
                "lon": 73.8567,
                "website": "https://goldenladle.example",
            },
            {
                "email": "hello@greenplate.com",
                "full_name": "Priya Sharma",
                "phone": "+91-9811000002",
                "org_name": "The Green Plate Bistro",
                "org_desc": "Farm-to-table bistro specialising in organic produce and prepared meals.",
                "address": "22, 80 Feet Road, Koramangala 4th Block, Bengaluru, Karnataka 560034",
                "lat": 12.9352,
                "lon": 77.6245,
            },
            {
                "email": "bakers@cornerhouse.com",
                "full_name": "Amit Kapoor",
                "phone": "+91-9811000003",
                "org_name": "Bakers Corner Bakehouse",
                "org_desc": "Artisan bakery producing fresh bread, pastries and confections every morning.",
                "address": "7, Hauz Khas Village, New Delhi, Delhi 110016",
                "lat": 28.5502,
                "lon": 77.2019,
            },
            {
                "email": "kitchen@coastaltable.com",
                "full_name": "Leena D'Souza",
                "phone": "+91-9811000008",
                "org_name": "Coastal Table",
                "org_desc": "Goa seafood kitchen sharing unsold lunch platters with nearby shelters.",
                "address": "21, 18th June Road, Panaji, Goa 403001",
                "lat": 15.4909,
                "lon": 73.8278,
            },
        ]

        restaurant_orgs = {}
        for r in restaurants_spec:
            u = make_user(db, r["email"], r["full_name"], r["phone"], UserRole.RESTAURANT, UserStatus.ACTIVE)
            org = make_org(
                db, u, r["org_name"], r["org_desc"], r["address"], r["lat"], r["lon"],
                website=r.get("website"),
            )
            restaurant_orgs[r["email"]] = org
            print(f"  Restaurant: {r['email']}")

        ngos_spec = [
            {
                "email": "info@hungerrelief.org",
                "full_name": "Sunita Pillai",
                "phone": "+91-9811000004",
                "org_name": "Hunger Relief Society",
                "org_desc": "Highest acceptance rate in Mumbai — redistributes surplus to 2000+ families across Dharavi.",
                "address": "Plot 6, Dharavi, Mumbai, Maharashtra 400017",
                "lat": 19.0330,
                "lon": 72.8566,
            },
            {
                "email": "contact@annadan.org",
                "full_name": "Meera Joshi",
                "phone": "+91-9811000006",
                "org_name": "Annadan Seva Trust",
                "org_desc": "Delhi community kitchens with excellent pickup reliability and grant-ready impact reports.",
                "address": "3, Janpath Lane, Connaught Place, New Delhi, Delhi 110001",
                "lat": 28.6315,
                "lon": 77.2167,
            },
            {
                "email": "team@feedthecity.org",
                "full_name": "Kiran Rao",
                "phone": "+91-9811000005",
                "org_name": "Feed The City Foundation",
                "org_desc": "Bengaluru NGO connecting surplus with daily-wage workers and night shelters.",
                "address": "12, Brigade Road, Bengaluru, Karnataka 560001",
                "lat": 12.9716,
                "lon": 77.6099,
            },
            {
                "email": "hello@plateforhope.org",
                "full_name": "Farhan Qureshi",
                "phone": "+91-9811000009",
                "org_name": "Plate for Hope",
                "org_desc": "Pune volunteer network running evening meal routes for pavement families.",
                "address": "44, JM Road, Pune, Maharashtra 411004",
                "lat": 18.5196,
                "lon": 73.8553,
            },
            {
                "email": "ops@sheltermeals.org",
                "full_name": "Nandini Rao",
                "phone": "+91-9811000010",
                "org_name": "Shelter Meals Collective",
                "org_desc": "Goa collective feeding construction workers and transit shelters.",
                "address": "9, Fontainhas, Panaji, Goa 403001",
                "lat": 15.4989,
                "lon": 73.8282,
            },
        ]

        ngo_orgs = {}
        for n in ngos_spec:
            u = make_user(db, n["email"], n["full_name"], n["phone"], UserRole.NGO, UserStatus.ACTIVE)
            org = make_org(db, u, n["org_name"], n["org_desc"], n["address"], n["lat"], n["lon"])
            ngo_orgs[n["email"]] = org
            print(f"  NGO: {n['email']}")

        pending_rest_user = make_user(
            db, "pending.kitchen@foodshare.io", "Vikram Sethi", "+91-9811000091",
            UserRole.RESTAURANT, UserStatus.PENDING,
        )
        make_org(
            db, pending_rest_user,
            "Lotus Leaf Cafe",
            "New cafe applying for donor verification. Documents pending admin review.",
            "5, Linking Road, Bandra West, Mumbai, Maharashtra 400050",
            19.0596, 72.8295, approved=False,
        )
        print("  Pending restaurant: pending.kitchen@foodshare.io")

        pending_ngo_user = make_user(
            db, "pending.ngo@foodshare.io", "Asha Verma", "+91-9811000092",
            UserRole.NGO, UserStatus.PENDING,
        )
        make_org(
            db, pending_ngo_user,
            "Warm Plate Initiative",
            "Newly registered NGO awaiting verification before claiming food.",
            "18, Lajpat Nagar, New Delhi, Delhi 110024",
            28.5677, 77.2433, approved=False,
        )
        print("  Pending NGO: pending.ngo@foodshare.io")

        spice = restaurant_orgs["contact@spicegarden.com"]
        ladle = restaurant_orgs["hello@goldenladle.com"]
        green = restaurant_orgs["hello@greenplate.com"]
        bakers = restaurant_orgs["bakers@cornerhouse.com"]
        coastal = restaurant_orgs["kitchen@coastaltable.com"]

        hunger = ngo_orgs["info@hungerrelief.org"]
        annadan = ngo_orgs["contact@annadan.org"]
        feed = ngo_orgs["team@feedthecity.org"]
        plate = ngo_orgs["hello@plateforhope.org"]
        shelter = ngo_orgs["ops@sheltermeals.org"]

        live = [
            (spice, "South Indian Thali Meals", "30 freshly packed thali meals in sealed containers.", "Prepared Meals", 30, "portions", 6),
            (spice, "Mixed Vegetable Curry Bulk", "12 kg mixed vegetable curry for community kitchens.", "Prepared Meals", 12, "kg", 8),
            (ladle, "Wedding Catering Surplus", "80 portions of dal, rice, and paneer from a cancelled banquet.", "Prepared Meals", 80, "portions", 5),
            (ladle, "Chapati & Raita Packs", "200 chapatis with 8 kg raita, packed for evening distribution.", "Prepared Meals", 200, "pieces", 7),
            (green, "Organic Salad Boxes", "20 refrigerated salad boxes with vinaigrette.", "Produce", 20, "boxes", 12),
            (green, "Whole Grain Bread Loaves", "8 large whole-grain loaves baked this morning.", "Bakery", 8, "loaves", 24),
            (bakers, "Assorted Pastry Box", "5 dozen croissants, danishes and rolls from the morning bake.", "Bakery", 60, "pieces", 10),
            (bakers, "Fresh Paneer and Dairy Packs", "15 kg paneer plus 20 litres milk. Keep chilled.", "Dairy", 15, "kg", 12),
            (coastal, "Fish Curry Rice Platters", "25 lunch platters leftover after the afternoon rush.", "Prepared Meals", 25, "portions", 4),
            (coastal, "Seasonal Fruit Crates", "4 crates of ripe bananas and papaya for same-day use.", "Produce", 4, "crates", 18),
        ]
        for org, title, desc, cat, qty, unit, hours in live:
            make_donation(
                db, org, title, desc, cat, qty, unit, hours,
                org.address, org.latitude, org.longitude, DonationStatus.AVAILABLE,
            )
            print(f"  Live listing: {title}")

        completed_pairs = [
            (spice, hunger, "Evening Rice & Sambar", "Prepared Meals", 120, "portions", 2),
            (spice, hunger, "Packed Breakfast Idlis", "Prepared Meals", 90, "portions", 5),
            (spice, hunger, "Vegetable Biryani Trays", "Prepared Meals", 70, "portions", 8),
            (spice, plate, "Curd Rice Packets", "Prepared Meals", 40, "portions", 3),
            (ladle, plate, "Banquet Dal Makhani", "Prepared Meals", 150, "portions", 4),
            (ladle, plate, "Pulao & Raita", "Prepared Meals", 110, "portions", 6),
            (ladle, hunger, "Event Dessert Cups", "Bakery", 80, "pieces", 9),
            (bakers, annadan, "Morning Bread Surplus", "Bakery", 48, "loaves", 1),
            (bakers, annadan, "Milk Bread & Buns", "Bakery", 36, "loaves", 7),
            (green, feed, "Salad & Wrap Boxes", "Produce", 32, "boxes", 2),
            (green, feed, "Grain Bowls", "Prepared Meals", 28, "portions", 11),
            (coastal, shelter, "Fish Thali Lunch", "Prepared Meals", 40, "portions", 3),
            (coastal, shelter, "Coconut Rice Packs", "Prepared Meals", 22, "portions", 10),
            (bakers, annadan, "Festival Sweet Boxes", "Bakery", 50, "boxes", 14),
        ]
        for org, ngo, title, cat, qty, unit, days_ago in completed_pairs:
            donation = make_donation(
                db, org, title, f"Completed handover of {qty} {unit}.", cat, qty, unit, 6,
                org.address, org.latitude, org.longitude, DonationStatus.COMPLETED,
                hours_ago=24 * days_ago + 3,
            )
            donation.expires_at = datetime.utcnow() - timedelta(days=max(days_ago - 1, 0), hours=1)
            make_allocation(db, donation, ngo, qty, AllocationStatus.COMPLETED, days_ago=days_ago)
            print(f"  Completed: {title} -> {ngo.name}")

        in_flight = make_donation(
            db, spice, "Tonight's Extra Rotis", "40 rotis packed and waiting for pickup tonight.",
            "Prepared Meals", 40, "portions", 5, spice.address, spice.latitude, spice.longitude,
            DonationStatus.ACCEPTED,
        )
        make_allocation(db, in_flight, hunger, 40, AllocationStatus.ACCEPTED)
        print("  In-flight claim: Tonight's Extra Rotis")

        db.commit()
        print("\nSeed complete. Demo logins (password Demo@1234 unless noted):")
        print("  ADMIN     admin@foodshare.io / Admin@1234")
        print("  High donor restaurants:")
        print("    contact@spicegarden.com")
        print("    hello@goldenladle.com")
        print("  Other restaurants:")
        print("    hello@greenplate.com")
        print("    bakers@cornerhouse.com")
        print("    kitchen@coastaltable.com")
        print("  High-acceptance NGOs:")
        print("    info@hungerrelief.org")
        print("    contact@annadan.org")
        print("  Other NGOs:")
        print("    team@feedthecity.org")
        print("    hello@plateforhope.org")
        print("    ops@sheltermeals.org")
        print("  Pending verification (cannot post/claim until admin approves):")
        print("    pending.kitchen@foodshare.io")
        print("    pending.ngo@foodshare.io")
        print("  Verify them as admin -> Verifications -> Approve Partner")
    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
