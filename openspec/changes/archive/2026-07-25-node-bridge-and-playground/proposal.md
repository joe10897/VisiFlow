## Why

To maximize open-source adoption and star velocity on GitHub, VisiFlow needs to serve both Python and JavaScript/TypeScript ecosystems. Since over 70% of Playwright users write tests in JS/TS, adding a Node.js bridge alongside PyPI publishing and an interactive Web Playground will make VisiFlow accessible to all developers and create a compelling visual demonstration.

## What Changes

- Add `http-daemon`: A lightweight FastAPI-backed HTTP daemon mode (`visiflow server`) exposed via Python CLI to serve vision queries to external processes.
- Add `node-bridge`: An npm package/JS library (`visiflow-js`) that enables Node.js Playwright scripts to communicate with the local VisiFlow daemon seamlessly.
- Add `web-playground`: An interactive local Web UI (`visiflow ui`) where developers can drag and drop screenshots, test queries, and inspect bounding boxes visually in real-time.
- Add `cli-interface`: A CLI entrypoint (`visiflow`) allowing users to launch the server, open the playground, or run direct visual matching commands from the terminal.
- Update `README.md`: Upgrade README with badges, a comparison matrix, animated visual demo assets, and JS/Python quickstarts.

## Capabilities

### New Capabilities

- `http-daemon`: Local REST API endpoint providing `/detect` and `/match` services.
- `node-bridge`: Node.js/TypeScript wrapper library for Playwright JS/TS integration.
- `web-playground`: Interactive local web UI for screenshot visualization and bounding box inspection.
- `cli-interface`: Terminal CLI providing `visiflow server`, `visiflow ui`, and `visiflow match`.

## Impact

- **Dependencies**: Adds `fastapi`, `uvicorn`, `python-multipart` (already present in environment) for the HTTP server and web UI.
- **Node.js**: Adds a lightweight Node.js SDK under `bindings/nodejs` ready for npm publishing.
