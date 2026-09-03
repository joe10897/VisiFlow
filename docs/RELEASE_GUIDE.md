# 🚀 VisiFlow Release & Publishing Guide

This guide outlines the process for building and releasing new versions of **VisiFlow** to **PyPI** (Python) and **npm** (`visiflow-js`).

---

## 1. Version Bump Checklist

Before releasing, make sure the version numbers are synchronized across the repository:

1. **`pyproject.toml`**:
   ```toml
   [project]
   version = "0.9.0"
   ```
2. **`bindings/nodejs/package.json`**:
   ```json
   {
     "name": "visiflow-js",
     "version": "0.9.0"
   }
   ```
3. **`visiflow/static/index.html`**:
   Update version label badge (e.g. `v0.9.0`).
4. **`README.md`**:
   Update PyPI and npm badges:
   ```markdown
   [![PyPI Release](https://img.shields.io/badge/PyPI-v0.9.0-blue?logo=pypi&logoColor=white)](https://pypi.org/project/visiflow/)
   [![npm Release](https://img.shields.io/badge/npm-v0.9.0-red?logo=npm&logoColor=white)](https://www.npmjs.com/package/visiflow-js)
   ```

---

## 2. Automated Publishing via GitHub Actions (Recommended)

VisiFlow includes a pre-configured GitHub Actions workflow (`.github/workflows/publish.yml`) that automatically builds and publishes both PyPI and npm packages whenever a new version tag is pushed:

```bash
# Tag the new release
git tag v0.9.0

# Push tag to GitHub
git push origin v0.9.0
```

GitHub Actions will automatically:
1. Build the Python distribution wheel and source tarball using `build`.
2. Upload to **PyPI** using `twine` (with `${{ secrets.PYPI_API_TOKEN }}`).
3. Publish `visiflow-js` to **npm** (with `${{ secrets.NPM_TOKEN }}`).

---

## 3. Manual Publishing Guide

If you need to publish packages manually from your local machine:

### Python Package (PyPI)

```bash
# 1. Ensure build tools are installed
pip install --upgrade pip build twine

# 2. Clean previous build artifacts
rm -rf dist/ build/ *.egg-info

# 3. Build wheel and source distribution
python -m build

# 4. Check built package
python -m twine check dist/*

# 5. Upload to PyPI
python -m twine upload dist/*
```

### Node.js Package (`visiflow-js` on npm)

```bash
# 1. Navigate to the Node.js bindings directory
cd bindings/nodejs

# 2. Login to npm (if not already logged in)
npm login

# 3. Publish to npm registry
npm publish --access public
```

---

## 4. Post-Release Verification

After publishing, verify the installation on a fresh environment:

```bash
# Verify PyPI
pip install --upgrade visiflow
visiflow --help
visiflow mcp

# Verify npm
npm install visiflow-js
```
