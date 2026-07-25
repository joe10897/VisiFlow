# 👁️ VisiFlow

[![PyPI version](https://img.shields.io/pypi/v/visiflow.svg)](https://pypi.org/project/visiflow/0.1.0/)
[![PyPI Release](https://img.shields.io/badge/PyPI-v0.1.0-blue?logo=pypi&logoColor=white)](https://pypi.org/project/visiflow/0.1.0/)
[![npm Release](https://img.shields.io/badge/npm-v0.1.0-red?logo=npm&logoColor=white)](https://www.npmjs.com/package/visiflow-js)
[![npm version](https://img.shields.io/npm/v/visiflow-js.svg)](https://www.npmjs.com/package/visiflow-js)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Supported Platforms](https://img.shields.io/badge/platforms-Windows%20%7C%20macOS%20%7C%20Linux-blue.svg)]()

**VisiFlow** is a fast, 100% local, visual-driven E2E automation testing framework for **Python** and **Node.js (TypeScript/JavaScript)** ecosystem, built for **Playwright** and **Selenium**.

It challenges traditional web automation by throwing away fragile HTML DOM selectors (XPath, IDs, CSS classes) and replacing them with a local computer vision pipeline (YOLO + EasyOCR) to locate and interact with elements exactly how a human does.

![VisiFlow Visual Banner](assets/visiflow_demo_banner.png)

---

## ⚡ Comparison: Why VisiFlow?

| Metric / Feature | Traditional DOM Selectors (XPath/CSS) | Cloud AI Automation (GPT-4o Vision API) | **VisiFlow (Our Local Core)** |
| :--- | :--- | :--- | :--- |
| **Maintenance Cost** | 🔴 Extremely High (Breaks on CSS/ID refactoring) | 🟢 Extremely Low (Zero selector maintenance) | 🟢 **Zero Maintenance (Visual-driven)** |
| **Execution Cost** | 🟢 $0 / Free | 🔴 Expensive ($0.01+ per screenshot query) | 🟢 **$0 / 100% Free Local Execution** |
| **Latency** | 🟢 < 10ms | 🔴 1.5s - 4.0s (Cloud latency & queues) | 🟡 **100ms - 250ms (Sub-second local CV)** |
| **Data Privacy** | 🟢 100% On-Premise | 🔴 Privacy Risks (Sends UI to external servers) | 🟢 **100% On-Premise & Private (Offline)** |
| **Ecosystem Support**| Python, JS/TS, Java | Vendor locked APIs | 🟢 **Python & Node.js (Playwright + Selenium)** |

---

## 📦 Installation

### Python Package ([PyPI v0.1.0](https://pypi.org/project/visiflow/0.1.0/))
```bash
pip install "visiflow[playwright,selenium]"
```

### Node.js Package ([npm v0.1.0](https://www.npmjs.com/package/visiflow-js))
```bash
npm install visiflow-js
```

---

## 💻 Quick Start

### 1. Python + Playwright

```python
from playwright.sync_api import sync_playwright
from visiflow import VisiPlaywrightPage

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://example.com/login")

    # Wrap Playwright Page
    visipage = VisiPlaywrightPage(page)

    # Visual automation via natural language text labels!
    visipage.visual_fill("Username", "admin_user")
    visipage.visual_fill("Password", "secret_pass")
    visipage.visual_click("Submit")

    # Verify visually
    if visipage.visual_wait_for("Welcome back!"):
        print("Logged in successfully!")

    browser.close()
```

### 2. Node.js (JavaScript / TypeScript) + Playwright

First, start the local VisiFlow daemon server in your terminal:
```bash
visiflow server
```

Then in your JavaScript/TypeScript Playwright script:
```javascript
const { chromium } = require('playwright');
const { VisiPage } = require('visiflow-js');

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();
    await page.goto('https://example.com/login');

    // Wrap JS Playwright Page
    const visipage = new VisiPage(page);

    // Visual actions in JS!
    await visipage.visualFill('Username', 'js_developer');
    await visipage.visualClick('Submit');

    await browser.close();
})();
```

---

## 🤖 Visual Click & Interaction Advantages

Why write automation scripts using VisiFlow's visual engine?

- **Zero DOM Selector Maintenance**: Web applications get refactored frequently. Standard Selenium/Playwright scripts break the moment an ID, class name, or HTML structure changes (e.g. `<button>` changes to a `<div>`). VisiFlow locates elements visually. If the screen says **"指標"** or **"Submit"** and looks like a button, VisiFlow will find it and click it.
- **DPR Auto-Scaling Protection**: Modern test suites run on screens with different Device Pixel Ratios (DPR) (e.g. 1.0x on Docker containers vs 2.0x Retina displays on macOS). VisiFlow transparently scales all vision coordinates back to original viewport mouse spaces, making click scripts fully cross-platform and portable.
- **Sub-Second Performance & 100% Privacy**: Unlike cloud-based AI automation APIs (e.g. GPT-4o Vision) which introduce 3-second network latency and raise data privacy concerns, VisiFlow runs completely locally on CPU/GPU.

---

## 🎨 Interactive Web Playground

Want to test VisiFlow's object detection & text matching on your webpage screenshots before writing tests? Launch the built-in interactive Web UI:

```bash
visiflow ui
```

This opens `http://localhost:8000/ui` in your browser, where you can drag & drop any screenshot image to inspect bounding boxes and test queries live in real-time!

---

## 🛠️ CLI Reference

VisiFlow comes with a CLI tool:

- `visiflow server [--port 8000]`: Start the local HTTP vision daemon.
- `visiflow ui`: Launch the interactive Web Playground UI in your browser.
- `visiflow match <screenshot_path> <query>`: Test matching query coordinates directly from terminal.

---

## 🛡️ License

MIT License. Built for global open-source developers.
