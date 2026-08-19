# FoodShare - Food Redistribution Platform

FoodShare is a production-ready web application designed to connect restaurants with excess food to local non-governmental organizations (NGOs) in real-time. By bridging the gap between food surplus and food insecurity, FoodShare minimizes food waste and streamlines secure logistics through automated allocation logic, mapping features, and QR-code handover verification.

---

## The Three Platform Modes (Roles)

FoodShare provides specialized interfaces and custom user experiences for three distinct roles:

### 1. Restaurant Portal (Donor Mode)
Designed for food businesses to list, track, and verify surplus food donations.
*   **Donation Creation & Management**: Create, edit, and delete listings specifying categories (e.g., Prepared Meals, Baked Goods, Fresh Produce), quantity/unit, preparation/expiry times, pickup windows, precise coordinates (interactive map picker), and photo uploads.
*   **Claim Requests Management**: View, approve, or reject incoming real-time donation requests from nearby NGOs.
*   **Secure QR Verification**: Verify pickup handovers on-site by scanning or manually inputting the unique QR code presented by the NGO helper.
*   **Verification Uploads**: Upload corporate registrations or business license documents for platform verification.
*   **Analytics Dashboard**: View analytics on total meals saved, active listings, and distributions via custom interactive SVG charts.

### 2. NGO Portal (Receiver Mode)
Designed for non-profit organizations to claim, manage, and verify food distribution.
*   **Browse Listings**: Browse active donations via an interactive map or a listing grid. Filter by category, keyword search, or maximum radius distance (with automatic browser geolocation support).
*   **Claiming System**: Claim required quantities of food, with automated race-condition protection to prevent double-claiming. Includes critical allergy warnings and food safety instructions.
*   **Claims Log & QR Handovers**: Track claim states (`REQUESTED`, `ACCEPTED`, `PICKED_UP`, `COMPLETED`, `CANCELLED`). Generate and present secure QR codes/tokens for restaurant staff to scan at pickup.
*   **Organization Verification**: Upload tax exemption (e.g., Section 80G/501(c)(3)) and NGO registration documents.
*   **Impact Analytics**: Track total claims, completed distribution logs, and total meals received.

### 3. Administrative Console (Admin Mode)
Designed for platform owners to moderate users, audit logs, and oversee operations.
*   **Verification Portal**: Review registration documents uploaded by Restaurants and NGOs, and approve or reject their access.
*   **User Management**: View all users; suspend, activate, or reactivate accounts.
*   **Dispute Resolution**: View and manage complaints or feedback filed by organizations regarding handovers or food quality.
*   **Audit Logging**: Access a complete, tamper-evident audit trail tracking all critical actions (auth events, state transitions, modifications).
*   **Data Exports**: Download analytics reports as PDF or CSV sheets.

---

## How to Launch the Platform

### Prerequisites
Ensure you have the following installed on your machine:
*   [Node.js](https://nodejs.org/) (v18 or higher)
*   [Python](https://www.python.org/) (v3.10 or higher)
*   [Git](https://git-scm.com/)

---

### Installation & Setup

1.  **Clone the Repository**:
    ```bash
    git clone <your-repo-url>
    cd food-redistribution-platform
    ```

2.  **Environment Configuration**:
    Copy the sample environment configuration and configure your secrets:
    *   Duplicate `.env.example` to `.env` in the root folder.
    *   Set your database connection. By default, the app is pre-configured to connect to a Neon PostgreSQL instance. If running locally, you can change this to a local PostgreSQL connection or use SQLite:
        ```env
        DATABASE_URL=postgresql://user:password@localhost:5432/foodshare
        # Or for SQLite:
        # DATABASE_URL=sqlite:///./food_redist.db
        ```
    *   Configure `JWT_SECRET_KEY` and other credentials inside `.env` as required.

3.  **Install Dependencies**:
    The root `package.json` contains a script to automatically install both frontend and backend packages:
    ```bash
    npm run install:all
    ```
    *This runs `npm install` inside the frontend directory and installs the Python requirements via `pip install -r backend/requirements.txt`.*

---

### Database Setup & Migrations

The database schemas can be built either automatically or manually using migrations:

*   **Automatic Generation**: Launching the backend FastAPI server automatically checks and builds all required database tables via SQLAlchemy metadata.
*   **Manual Migrations (Alembic)**: If you are making schema adjustments or running in production, run Alembic migrations from the backend directory:
    ```bash
    cd backend
    alembic upgrade head
    cd ..
    ```
*   **Seed Sample Demo Data**:
    To pre-populate the database with test profiles, listings, and dummy logs, run the database seed script:
    ```bash
    python backend/seed.py
    ```

---

### Running the Application

You can launch the frontend and backend concurrently using the root package runner, or start them individually in separate terminals.

#### Option A: Concurrent Start (Recommended)
From the root directory, run:
```bash
npm run dev
```
*This uses `concurrently` to launch the FastAPI server (port `8000`) and the Vite React server (port `5173`) at the same time.*

#### Option B: Separate Terminal Launch
*   **Start Backend**:
    ```bash
    npm run dev:backend
    ```
    *(Equivalent to running `cd backend && python -m uvicorn app.main:app --reload --port 8000`)*
*   **Start Frontend**:
    ```bash
    npm run dev:frontend
    ```
    *(Equivalent to running `npm run dev --prefix frontend`)*

---

## Default Login Credentials (Seeded Data)

If you ran the seed script (`python backend/seed.py`), you can log in with the following default accounts:

*   **Platform Administrator**:
    *   **Email**: `admin@foodshare.io`
    *   **Password**: `Admin@1234`
*   **Restaurant / NGO Accounts**:
    *   **Password for all seed accounts**: `Demo@1234`
    *   **Sample Restaurant Email**: `contact@spicegarden.com`
    *   **Sample NGO Email**: `hope.foundation@ngo.org` (or check `backend/seed.py` for other seeded accounts)
