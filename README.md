# Backend — Donation OpenHand

Backend API for the **OpenHands** donation platform: user and NGO authentication, pickup requests, refundable deposit payments (Razorpay), and admin management. Built with **FastAPI**, **SQLModel**, and JWT auth.

## Quick start

### 1. Install dependencies

```bash
conda create -n dona python=3.12
conda activate dona
pip install -r requirements.txt
```

### 2. Configure environment

Copy `.env.example` to `.env` and set at least `SECRET_KEY`. See [doc/05-configuration.md](doc/05-configuration.md) for all options (database, email, Razorpay).

### 3. Run the app

```bash
uvicorn app.main:app --reload
```

- **API base:** [http://localhost:8000](http://localhost:8000)  
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)  
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Documentation

Detailed docs are in **[doc/](doc/)** (numbered 01–06 for reading order). Many include **Mermaid diagrams** (architecture, flows, data model, auth); render in GitHub, VS Code, or any Mermaid viewer.


| Doc                                                     | Description                                                |
| ------------------------------------------------------- | ---------------------------------------------------------- |
| [doc/README.md](doc/README.md)                          | Documentation index and diagram list                       |
| [01-system-design](doc/01-system-design.md)             | Architecture, flows, pickup lifecycle, end-to-end sequence |
| [02-api-design](doc/02-api-design.md)                   | REST API reference                                         |
| [03-data-model-design](doc/03-data-model-design.md)     | Database schema (5 diagram views)                          |
| [04-authentication](doc/04-authentication.md)           | JWT, roles, verification flows                             |
| [05-configuration](doc/05-configuration.md)             | Env vars, config flow, deployment                          |
| [06-presentation-points](doc/06-presentation-points.md) | PPT cheat sheet and “system at a glance” diagram           |


## Default credentials (development)

- **Admin:** `admin@gmail.com` / `Admin@123` (created on first run if missing)
- **Test NGOs:** See seed output in console; e.g. `ngo1@test.com`, `ngo2@test.com` with password `Test@1234` when NGO table is empty.

