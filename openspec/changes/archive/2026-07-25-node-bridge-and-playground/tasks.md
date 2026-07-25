## 1. HTTP Daemon & CLI Implementation

- [x] 1.1 Implement FastAPI HTTP server in `visiflow/server.py` (`/match`, `/detect` endpoints)
- [x] 1.2 Implement CLI entrypoint in `visiflow/cli.py` (`visiflow server`, `visiflow ui`, `visiflow match`)

## 2. Web Playground UI Implementation

- [x] 2.1 Build single-page glassmorphic UI in `visiflow/static/index.html` with Canvas overlay for bounding boxes
- [x] 2.2 Serve static Web Playground from `visiflow ui`

## 3. Node.js Bridge (visiflow-js)

- [x] 3.1 Create npm package layout under `bindings/nodejs` (`package.json`, `index.js`, `README.md`)
- [x] 3.2 Implement `VisiPage` for Playwright JS/TS communicating with HTTP daemon
- [x] 3.3 Create Node.js test example script `bindings/nodejs/example.js`

## 4. GitHub Promotional Assets & README Upgrade

- [x] 4.1 Create visual demo generator script `tools/generate_demo_assets.py`
- [x] 4.2 Upgrade `README.md` with comparison matrix, JS quickstart, and badges
