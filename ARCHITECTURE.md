# Harvest Link architecture reference

The persistent source graph lives in `graphify-out/graph.json`; the navigable
summary is `graphify-out/GRAPH_REPORT.md`. Rebuild with `graphify update .` after
changing module boundaries, routes, models, or dependencies. Use `graphify query`
and `graphify affected` before editing high-impact modules, then read the source
for the actual behavior.

## Runtime shape

- `frontend/`: React 19 + TypeScript + Vite single-page application. `App.tsx`
  dispatches routes to public pages and the restaurant, NGO, and admin portals.
- `frontend/src/context/AuthContext.tsx`: login/profile/session state.
  `frontend/src/services/api.ts`: Axios API client and refresh-token rotation.
- `backend/app/main.py`: FastAPI application, CORS, headers, rate limiting,
  safe errors, public image mount, health check, and API router registration.
- `backend/app/api/`: thin role-aware API handlers. `deps.py` is the server-side
  authentication/authorization boundary. Frontend routing is UX only.
- `backend/app/crud/crud.py`: current business services for registration,
  verification, donations, claims, QR handovers, complaints, and audit logs.
- `backend/app/models/models.py`: SQLAlchemy models. PostgreSQL is the intended
  production database; SQLite is supported for local development and tests.
- `backend/alembic/versions/`: baseline schema and single-administrator index.
- `backend/bootstrap_admin.py`: environment-driven one-admin bootstrap.
- `backend/app/utils/`: local/S3 storage, in-app/SMTP notifications, PDF/CSV reports.

## Critical dependency chains

```text
Login -> AuthContext -> api.ts -> /auth/login -> password verification -> User/AuthToken
RestaurantPortal -> /donations -> restaurant dependency -> create/update_donation -> Donation
NGOPortal -> /allocations -> NGO dependency -> create_allocation -> DonationAllocation + locked Donation
RestaurantPortal / NGOPortal -> /qr/verify -> verify_qr_scan -> allocation and donation state
AdminPortal -> /admin -> admin dependency -> verification/status/report services -> models
Profile documents -> /users/documents -> upload validation -> private local/S3 storage
Admin document download -> /admin/documents/{id}/download -> admin dependency -> private file
```

## Data relationships and boundaries

- A `User` has at most one `Organization`; users have roles and account status.
- Organizations own donations, receive allocations, and submit verification documents.
- A donation can be split across allocations; requests reserve quantity until
  accepted/rejected/cancelled. QR events record pickup/completion transitions.
- Notifications and authentication tokens belong to a user. Audit logs retain
  actor/target references. Complaints link reporters, optional reported users,
  and optional donations.
- A partial unique index permits at most one ADMIN role. Public registration
  cannot create admins, and admin self-suspension is blocked.
- Access/refresh/reset tokens are stored as one-way hashes. Role and status are
  always loaded from the database. Logout/password changes revoke stored sessions.
- Verification documents are not publicly mounted. Images remain public assets.

## High-impact areas

Graphify identifies `User`, `UserRole`, `Donation`, `create_audit_log`,
`DonationAllocation`, `verify_qr_scan`, `create_notification`, and `useAuth` as
highly connected modules. Changes here require authentication, authorization,
donation lifecycle, and portal regression tests.

No import cycles were detected. The large `crud.py` and portal components remain
coupled; they are retained to preserve behavior rather than split solely by size.
`OrganizationUpdate`, `get_user_by_id`, and `transactional_session` are exported
or architectural helpers with weak usage evidence; they are retained rather
than deleted on inference alone.

## Graph limits

The graph records structural imports/calls and some inferred relationships. It
does not prove runtime permissions, API string routes, transaction correctness,
CSS usage, or deployment behavior. Those require source inspection and tests.
The generated graph reports its own extracted/inferred ratio and source locations.
