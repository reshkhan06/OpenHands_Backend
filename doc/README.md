# Donation OpenHand — Backend Documentation

This folder contains documentation for the **Donation OpenHand** backend: system design, API design, data models, authentication, and configuration. Use these documents to onboard developers or explain the system to stakeholders. Many sections include **Mermaid diagrams** (flowcharts, sequence diagrams, ER diagrams, state diagrams)—render them in GitHub, VS Code, or any Mermaid-compatible viewer for a clearer picture.

## Documentation Index

| Document | Description |
|----------|-------------|
| [01-system-design.md](01-system-design.md) | High-level architecture, components, and flows |
| [02-api-design.md](02-api-design.md) | REST API reference: endpoints, request/response, auth |
| [03-data-model-design.md](03-data-model-design.md) | Database schema, entities, and relationships |
| [04-authentication.md](04-authentication.md) | Auth model: JWT, roles, and dependency injection |
| [05-configuration.md](05-configuration.md) | Environment variables, setup, and deployment |
| [06-presentation-points.md](06-presentation-points.md) | Bullet-point cheat sheet for PPT/talks — explain without opening code |

## Where to find diagrams

| Doc | Diagrams |
|-----|----------|
| 01-system-design | Architecture (flowchart), request flow (sequence), pickup state machine, **end-to-end pickup+payment sequence** |
| 02-api-design | API router overview |
| 03-data-model-design | **5 views:** ER, UML class, visual schema boxes, domain flow, relationship flow |
| 04-authentication | Token → dependencies, auth sequence, **donor vs NGO verification flow** |
| 05-configuration | **Config flow:** which env vars feed which part of the app |
| 06-presentation-points | Bullet points (no diagrams) |

## Quick Links

- **Run the backend:** `uvicorn app.main:app --reload` (see [05-configuration.md](05-configuration.md))
- **API base URL (local):** `http://localhost:8000`
- **Interactive API docs:** `http://localhost:8000/docs` (Swagger UI)
