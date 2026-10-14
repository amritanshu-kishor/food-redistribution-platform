# Graph Report - rest  (2026-10-12)

## Corpus Check
- 60 files · ~53,830 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 7 file(s) not represented in the graph (top: (none) 3, .example 1, .ini 1)

## Summary
- 640 nodes · 1749 edges · 29 communities (19 shown, 10 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 250 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `81510de1`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- allocations.py
- schemas.py
- User
- NGOPortal.tsx
- frontend/package.json
- users.py
- compilerOptions
- compilerOptions
- How to Launch the Platform
- reports.py
- scripts
- get_my_notifications
- .oxlintrc.json
- test_main.py
- Harvest Link architecture reference
- React + TypeScript + Vite
- tsconfig.json
- production.md
- auth.py
- crud.py
- sqlalchemy
- rate_limit.py
- scan_qr_code
- main.py
- get_profile
- get_allocation_details

## God Nodes (most connected - your core abstractions)
1. `User` - 76 edges
2. `UserRole` - 42 edges
3. `Donation` - 32 edges
4. `create_audit_log()` - 31 edges
5. `UserStatus` - 31 edges
6. `DonationStatus` - 26 edges
7. `DonationAllocation` - 24 edges
8. `verify_qr_scan()` - 22 edges
9. `AllocationStatus` - 22 edges
10. `create_notification()` - 21 edges

## Surprising Connections (you probably didn't know these)
- `High-impact areas` --references--> `transactional_session()`  [INFERRED]
  ARCHITECTURE.md → backend/app/core/database.py
- `High-impact areas` --references--> `UserRole`  [INFERRED]
  ARCHITECTURE.md → backend/app/models/models.py
- `High-impact areas` --references--> `DonationAllocation`  [INFERRED]
  ARCHITECTURE.md → backend/app/models/models.py
- `High-impact areas` --references--> `OrganizationUpdate`  [INFERRED]
  ARCHITECTURE.md → backend/app/schemas/schemas.py
- `High-impact areas` --references--> `useAuth()`  [INFERRED]
  ARCHITECTURE.md → frontend/src/context/AuthContext.tsx

## Import Cycles
- None detected.

## Communities (29 total, 10 thin omitted)

### Community 0 - "allocations.py"
Cohesion: 0.24
Nodes (4): get_current_active_user(), _enable_sqlite_foreign_keys(), get_db(), transactional_session()

### Community 1 - "schemas.py"
Cohesion: 0.10
Nodes (32): failed_result(), AllocationBase, AllocationCreate, AllocationOut, AuditLogOut, ChangePasswordRequest, ComplaintCreate, ComplaintOut (+24 more)

### Community 2 - "User"
Cohesion: 0.07
Nodes (44): run_migrations_offline(), run_migrations_online(), change_user_status(), download_document(), download_reports(), get_dashboard_metrics(), list_audit_logs(), list_complaints() (+36 more)

### Community 3 - "NGOPortal.tsx"
Cohesion: 0.07
Nodes (60): AdminPortal, App(), AppContent(), Landing, Login, NGOPortal, Register, RestaurantPortal (+52 more)

### Community 4 - "frontend/package.json"
Cohesion: 0.04
Nodes (46): dependencies, axios, html5-qrcode, leaflet, lucide-react, qrcode.react, react, react-dom (+38 more)

### Community 5 - "users.py"
Cohesion: 0.15
Nodes (6): submit_complaint(), update_profile(), upload_verification_document(), delete_uploaded_file(), save_uploaded_file(), validate_file()

### Community 6 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowArbitraryExtensions, allowImportingTsExtensions, erasableSyntaxOnly, jsx, lib, module, moduleDetection (+11 more)

### Community 7 - "compilerOptions"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, noEmit, noFallthroughCasesInSwitch (+8 more)

### Community 8 - "How to Launch the Platform"
Cohesion: 0.14
Nodes (13): 1. Restaurant Portal (Donor Mode), 2. NGO Portal (Receiver Mode), 3. Administrative Console (Admin Mode), Database Setup & Migrations, FoodShare - Food Redistribution Platform, How to Launch the Platform, Installation & Setup, Option A: Concurrent Start (Recommended) (+5 more)

### Community 11 - "scripts"
Cohesion: 0.12
Nodes (15): description, devDependencies, concurrently, name, scripts, bootstrap:admin, build, dev (+7 more)

### Community 12 - "get_my_notifications"
Cohesion: 0.25
Nodes (3): get_my_notifications(), mark_all_notifications_read(), mark_single_notification_read()

### Community 13 - ".oxlintrc.json"
Cohesion: 0.33
Nodes (5): plugins, rules, react/only-export-components, react/rules-of-hooks, $schema

### Community 14 - "test_main.py"
Cohesion: 0.08
Nodes (22): Settings, accepted_claim(), client(), db_session(), enforce_foreign_keys(), published_food(), setup_db(), test_browse_subtracts_pending_reservations() (+14 more)

### Community 15 - "Harvest Link architecture reference"
Cohesion: 0.33
Nodes (5): Critical dependency chains, Data relationships and boundaries, Graph limits, Harvest Link architecture reference, Runtime shape

### Community 16 - "React + TypeScript + Vite"
Cohesion: 0.50
Nodes (3): Expanding the Oxlint configuration, React Compiler, React + TypeScript + Vite

### Community 21 - "auth.py"
Cohesion: 0.09
Nodes (20): change_password(), forgot_password(), login(), logout(), _persist_access_token(), refresh(), register(), reset_password() (+12 more)

### Community 22 - "crud.py"
Cohesion: 0.09
Nodes (35): High-impact areas, browse_donations(), create_new_donation(), edit_donation(), get_donation_details(), get_my_listings(), haversine_distance(), upload_donation_image() (+27 more)

### Community 26 - "main.py"
Cohesion: 0.15
Nodes (5): health_check(), request_validation_error(), root(), security_headers(), unhandled_exception()

### Community 29 - "get_allocation_details"
Cohesion: 0.17
Nodes (6): approve_claim(), claim_food_allocation(), decline_claim(), get_allocation_details(), get_incoming_claims(), get_my_claims()

## Knowledge Gaps
- **11 isolated node(s):** `@types/leaflet`, `@tailwindcss/postcss`, `@types/node`, `@types/react`, `@types/react-dom` (+6 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 282 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **10 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `High-impact areas` connect `crud.py` to `allocations.py`, `schemas.py`, `User`, `NGOPortal.tsx`, `Harvest Link architecture reference`?**
  _High betweenness centrality (0.283) - this node is a cross-community bridge._
- **Are the 51 inferred relationships involving `User` (e.g. with `change_user_status()` and `download_document()`) actually correct?**
  _`User` has 51 INFERRED edges - model-reasoned connections that need verification._
- **What connects `@types/leaflet`, `@tailwindcss/postcss`, `@types/node` to the rest of the system?**
  _11 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `schemas.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09693877551020408 - nodes in this community are weakly interconnected._
- **Why does `useAuth()` connect `NGOPortal.tsx` to `crud.py`?**
  _High betweenness centrality (0.268) - this node is a cross-community bridge._
- **Are the 28 inferred relationships involving `UserRole` (e.g. with `High-impact areas` and `get_dashboard_metrics()`) actually correct?**
  _`UserRole` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Should `User` be split into smaller, more focused modules?**
  _Cohesion score 0.06635318704284221 - nodes in this community are weakly interconnected._