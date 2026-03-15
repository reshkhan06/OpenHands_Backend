# Presentation Points — Backend

**Use this as a cheat sheet to explain the backend in a PPT without opening the code.** Bullet points are ordered for a typical slide flow.

---

## System at a glance

```mermaid
flowchart TB
    subgraph Clients["Who calls the API"]
        Donor[Donor]
        NGO[NGO]
        Admin[Admin]
    end
    subgraph Backend["FastAPI Backend"]
        UserAPI[/user: signup, login, me]
        NgoAPI[/ngo: register, login, list, me]
        Verify[/verify]
        Pickups[/pickups]
        Payments[/payments]
        AdminAPI[/admin]
    end
    subgraph Storage["Storage & external"]
        DB[(Database\nusers, ngos, pickups\npayments, config)]
        SMTP[SMTP\nemails]
        RZ[Razorpay]
    end
    Donor --> UserAPI
    Donor --> Pickups
    Donor --> Payments
    NGO --> NgoAPI
    NGO --> Pickups
    Admin --> AdminAPI
    UserAPI --> DB
    NgoAPI --> DB
    Verify --> DB
    Verify --> SMTP
    Pickups --> DB
    Pickups --> RZ
    Payments --> DB
    Payments --> RZ
    AdminAPI --> DB
```

---

## 1. What Is the System?

- **OpenHands (Donation OpenHand)** — a donation platform that connects **donors** who want to give items with **NGOs** who collect them.
- Donors **request a pickup** → choose an **NGO** → pay a **refundable deposit** (Razorpay) → NGO **accepts and manages** the pickup; deposit is **refunded on completion**.
- **Admins** approve NGOs, manage users, and configure the system (e.g. deposit amount).

---

## 2. Three Actor Roles

| Role | Who | Main actions |
|------|-----|----------------|
| **Donor** | Registered user | Sign up, verify email, create pickup, pay deposit, track status |
| **NGO** | Registered organization | Sign up, verify email, get approved by admin, log in, accept/manage pickups, update status |
| **Admin** | Special user | Manage users (block/role), approve/reject NGOs, view dashboard, set deposit amount |

---

## 3. High-Level Architecture (One Slide)

- **Frontend** (React/Vite) talks to **Backend** (FastAPI) over HTTP/JSON; CORS enabled for frontend origin.
- **Backend** uses: **Database** (SQLite/PostgreSQL via SQLModel), **SMTP** (verification & notification emails), **Razorpay** (create order, verify payment, refund on completion).
- **Auth**: JWT in `Authorization: Bearer <token>`; separate tokens for **users** (donor/admin) vs **NGOs**.

---

## 4. Main Flows (No Code)

**Donor journey**

1. Sign up → verification email sent.
2. Click link → email verified.
3. Log in → get JWT.
4. Create pickup: choose NGO, address, optional schedule/description → backend creates deposit order (Razorpay) → donor pays on frontend.
5. Frontend confirms payment with backend → NGO gets email about new pickup.
6. Donor sees status updates (requested → accepted → on the way → picked up → completed).

**NGO journey**

1. Register → verification email.
2. Verify email → admin gets notified; NGO stays “pending” until admin approves.
3. Admin approves → NGO can log in.
4. NGO sees pickups, accepts, updates status (on the way, picked up, completed).
5. When status = completed, backend can trigger refund of deposit.

**Admin**

- Dashboard: total users, NGOs, pickups, pending NGOs, active deposits.
- List/filter users and NGOs; block user, change role; approve/delete NGO.
- List/filter pickups; view config; set deposit amount (e.g. in paise).

---

## 5. API Areas (Routers)

- **User** — signup, login, profile, change-password, delete (by email).
- **NGO** — register, login, list (verified only), NGO profile.
- **Verify** — unified email verification for both user and NGO; notifies admin when NGO verifies.
- **Pickups** — create (donor/admin), list/get (donor or NGO), update status (NGO/admin).
- **Payments** — confirm payment (Razorpay signature), get payment by pickup; optional webhook.
- **Admin** — dashboard stats, users CRUD, NGOs CRUD, pickups list/detail, config get/update.

---

## 6. Data (What We Store)

- **users** — donors and admins: profile, hashed password (Argon2), email verification, is_active.
- **ngos** — organizations: profile, bank details, verification token, is_verified (set by admin).
- **pickups** — donor_id, ngo_id, address, status, scheduled_time, items_description; links to payment.
- **payments** — Razorpay order_id, payment_id, amount, status, refund state.
- **pickup_status_history** — who changed status, when, optional note.
- **admin_config** — e.g. deposit_amount_paise.

---

## 7. Security & Auth (Talking Points)

- **Passwords**: Argon2 hash; never stored in plain text.
- **JWT**: Two kinds — user token (user_id) and NGO token (ngo_id); backend knows who is calling.
- **Email verification**: Required before login for both users and NGOs.
- **NGO approval**: Admin must set NGO as verified before NGO can log in.
- **Role checks**: Endpoints use dependencies (e.g. require donor, or NGO, or admin) and return 401/403 when not allowed.

---

## 8. Integrations

- **Razorpay**: Create order when pickup is created; frontend pays; backend verifies signature on confirm; refund when pickup is completed (if configured).
- **Email (SMTP)**: Verification links (user & NGO), pickup request to NGO, status update to donor, new NGO to admin, etc.
- **Database**: SQLModel (SQLAlchemy); default SQLite; can switch to PostgreSQL via `DATABASE_URL`.

---

## 9. Tech Stack (One Line Each)

- **Framework**: FastAPI.
- **ORM / DB**: SQLModel; SQLite / PostgreSQL.
- **Auth**: JWT (HS256), Argon2 for passwords.
- **Payments**: Razorpay (orders, verify, refund).
- **Email**: SMTP (e.g. Gmail); HTML templates for verification, notifications.
- **Docs**: Swagger UI at `/docs`; base URL e.g. `http://localhost:8000`.

---

## 10. Quick Numbers / Facts

- **Three roles**: donor, NGO, admin.
- **Two token types**: user JWT, NGO JWT.
- **Pickup status flow**: requested → accepted → on_the_way → picked_up → completed (or cancelled).
- **Deposit**: Refundable; amount configurable by admin (stored in paise).
- **Run locally**: `uvicorn app.main:app --reload`; API docs at `/docs`.

Use this doc to structure slides: problem/solution → roles → architecture → flows → API → data → security → integrations → tech stack.
