## Context

To enable Node.js developers and provide an interactive demo experience for GitHub promotion, VisiFlow requires an HTTP daemon server layer, a Node.js client library (`visiflow-js`), a CLI tool (`visiflow`), and a local Web Playground UI.

## Goals / Non-Goals

**Goals:**
- Provide a zero-configuration HTTP REST API powered by FastAPI/uvicorn.
- Package `visiflow-js` as an npm module supporting Playwright Node.js bindings.
- Provide `visiflow ui` delivering a sleek, glassmorphic drag-and-drop web UI for real-time bounding box inspection.
- Provide `visiflow server` and `visiflow match` CLI utilities.

**Non-Goals:**
- Hosting a public cloud API (the daemon runs strictly on `localhost`).

## Decisions

### Decision 1: Daemon Protocol - HTTP REST vs WebSockets
We will use **HTTP REST with base64/multipart screenshot uploads**.
- **Rationale**: HTTP REST is simple, reliable, and easily consumable across languages without persistent connection overhead.

### Decision 2: Web Playground Design
We will build a single-page HTML/JS application served directly by FastAPI.
- **Rationale**: Zero extra build tools required. It loads in any browser natively from `visiflow ui`.

## Risks / Trade-offs

- **[Risk] Port Conflict on 8000** → *Mitigation*: Allow configuring port via CLI option `--port`.
