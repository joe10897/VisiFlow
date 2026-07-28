// Controller logic for the Chrome Extension Popup

let localServerUrl = "http://localhost:8000";
let recordedSteps = [];
let isScanning = false;

const statusBadge = document.getElementById("status");
const statusText = document.getElementById("status-text");
const scanBtn = document.getElementById("scan-btn");
const scanLoader = document.getElementById("scan-loader");
const scriptBox = document.getElementById("script-box");
const langSelect = document.getElementById("lang-select");
const copyBtn = document.getElementById("copy-btn");
const clearBtn = document.getElementById("clear-btn");
const hideOverlaysBtn = document.getElementById("hide-overlays-btn");
const runBtn = document.getElementById("run-btn");
const stepsListContainer = document.getElementById("steps-list");

let activeTabUrl = "https://example.com";

// Check connection to local VisiFlow FastAPI server on load
checkConnection();
loadState();

// Get the URL of the active webpage tab being recorded
chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
  if (tabs && tabs[0] && tabs[0].url) {
    // Avoid setting to chrome extension internal page URL
    if (!tabs[0].url.startsWith("chrome-extension://")) {
      activeTabUrl = tabs[0].url;
    }
  }
});

function checkConnection() {
  fetch(localServerUrl + "/")
    .then(resp => resp.json())
    .then(data => {
      if (data.status === "ok") {
        statusBadge.classList.add("connected");
        statusText.textContent = "Connected";
      } else {
        setDisconnected();
      }
    })
    .catch(() => {
      setDisconnected();
    });
}

function setDisconnected() {
  statusBadge.classList.remove("connected");
  statusText.textContent = "Disconnected";
}

// Load recorded steps from chrome storage if they exist
function loadState() {
  chrome.storage.local.get(["recordedSteps", "selectedLanguage"], (res) => {
    if (res.recordedSteps) {
      recordedSteps = res.recordedSteps;
      renderStepsList();
      updateScriptOutput();
    }
    if (res.selectedLanguage) {
      langSelect.value = res.selectedLanguage;
    }
  });
}

function renderStepsList() {
  stepsListContainer.innerHTML = "";
  
  if (recordedSteps.length === 0) {
    // Show empty state with an "Add Step" button
    stepsListContainer.innerHTML = `
      <div style="color: var(--text-muted); font-size: 0.78rem; text-align: center; padding: 8px 0;">No steps recorded. Scan page and click overlays to add steps.</div>
      <div style="display:flex; justify-content:center; margin-top:6px;">
        <div class="step-btn-add" id="add-first-step" title="Add a blank step" style="width:auto; padding:3px 10px; font-size:0.78rem; gap:4px;">＋ Add Step</div>
      </div>`;
    document.getElementById("add-first-step").addEventListener("click", () => {
      recordedSteps.push({ action: "click", target: "", value: null });
      chrome.storage.local.set({ recordedSteps });
      renderStepsList();
      updateScriptOutput();
    });
    return;
  }
  
  recordedSteps.forEach((step, idx) => {
    const row = document.createElement("div");
    row.className = "step-row";
    
    // ── ↑↓ Order Controls ──────────────────────────────────────
    const orderCtrl = document.createElement("div");
    orderCtrl.className = "step-controls";

    const upBtn = document.createElement("button");
    upBtn.className = "step-btn-move";
    upBtn.innerHTML = "▲";
    upBtn.title = "Move up";
    upBtn.disabled = idx === 0;
    upBtn.addEventListener("click", () => {
      [recordedSteps[idx - 1], recordedSteps[idx]] = [recordedSteps[idx], recordedSteps[idx - 1]];
      chrome.storage.local.set({ recordedSteps });
      renderStepsList();
      updateScriptOutput();
    });

    const downBtn = document.createElement("button");
    downBtn.className = "step-btn-move";
    downBtn.innerHTML = "▼";
    downBtn.title = "Move down";
    downBtn.disabled = idx === recordedSteps.length - 1;
    downBtn.addEventListener("click", () => {
      [recordedSteps[idx + 1], recordedSteps[idx]] = [recordedSteps[idx], recordedSteps[idx + 1]];
      chrome.storage.local.set({ recordedSteps });
      renderStepsList();
      updateScriptOutput();
    });

    orderCtrl.appendChild(upBtn);
    orderCtrl.appendChild(downBtn);
    row.appendChild(orderCtrl);

    // ── Step Number ────────────────────────────────────────────
    const num = document.createElement("div");
    num.className = "step-num";
    num.textContent = idx + 1;
    row.appendChild(num);
    
    // ── Action Dropdown (Click, Fill or Key) ────────────────────
    const select = document.createElement("select");
    select.className = "step-select";
    select.innerHTML = `
      <option value="click" ${step.action === "click" ? "selected" : ""}>Click</option>
      <option value="fill" ${step.action === "fill" ? "selected" : ""}>Fill</option>
      <option value="key" ${step.action === "key" ? "selected" : ""}>Key</option>
    `;
    select.addEventListener("change", (e) => {
      step.action = e.target.value;
      if (step.action === "fill" && !step.value) step.value = "text";
      if (step.action === "key") {
        step.target = "{enter}";
        step.value = null;
      }
      chrome.storage.local.set({ recordedSteps });
      renderStepsList();
      updateScriptOutput();
    });
    row.appendChild(select);
    
    // ── Target Input ───────────────────────────────────────────
    const targetInput = document.createElement("input");
    targetInput.type = "text";
    targetInput.className = "step-input";
    targetInput.value = step.target || "";
    targetInput.placeholder = step.action === "key" ? "Key e.g. {enter}" : "Visual target label";
    targetInput.addEventListener("input", (e) => {
      step.target = e.target.value;
      chrome.storage.local.set({ recordedSteps });
      updateScriptOutput();
    });
    row.appendChild(targetInput);
    
    // ── Value Input (Fill only) ────────────────────────────────
    if (step.action === "fill") {
      const valInput = document.createElement("input");
      valInput.type = "text";
      valInput.className = "step-input";
      valInput.value = step.value || "";
      valInput.placeholder = "Value to type";
      valInput.style.borderColor = "var(--accent-emerald)";
      valInput.addEventListener("input", (e) => {
        step.value = e.target.value;
        chrome.storage.local.set({ recordedSteps });
        updateScriptOutput();
      });
      row.appendChild(valInput);
    }
    
    // ── + Add Step below ───────────────────────────────────────
    const addBtn = document.createElement("div");
    addBtn.className = "step-btn-add";
    addBtn.innerHTML = "＋";
    addBtn.title = "Insert a blank step below";
    addBtn.addEventListener("click", () => {
      recordedSteps.splice(idx + 1, 0, { action: "click", target: "", value: null });
      chrome.storage.local.set({ recordedSteps });
      renderStepsList();
      updateScriptOutput();
    });
    row.appendChild(addBtn);

    // ── Delete Button ──────────────────────────────────────────
    const delBtn = document.createElement("div");
    delBtn.className = "step-btn-del";
    delBtn.innerHTML = "✕";
    delBtn.title = "Delete Step";
    delBtn.addEventListener("click", () => {
      recordedSteps.splice(idx, 1);
      chrome.storage.local.set({ recordedSteps });
      renderStepsList();
      updateScriptOutput();
    });
    row.appendChild(delBtn);
    
    stepsListContainer.appendChild(row);
  });
}


// Trigger screen capture and local YOLO/OCR element detection
scanBtn.addEventListener("click", () => {
  if (isScanning) return;
  isScanning = true;
  scanLoader.style.display = "inline-block";
  scanBtn.innerHTML = '<span class="loader" id="scan-loader" style="display: inline-block;"></span> 🔄 Scanning Page...';
  scanBtn.disabled = true;
  scriptBox.value = "// Capturing viewport and extracting layout coordinates with local YOLOv26n & EasyOCR models...";

  // 1. Tell background service worker to capture viewport and call VisiFlow local server
  chrome.runtime.sendMessage({ action: "captureAndDetect" }, (response) => {
    isScanning = false;
    scanBtn.innerHTML = '<span>📸 Scan Web Elements</span>';
    scanBtn.disabled = false;

    if (!response || response.status === "error") {
      alert("Scan failed: " + (response ? response.message : "Unknown error connecting to background worker."));
      return;
    }

    const elements = response.data.elements || [];
    const ocr = response.data.ocr || [];

    // 2. Query the active browser tab to inject content.js and draw overlays
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (!tabs.length) return;
      const activeTabId = tabs[0].id;

      // Inject content script if not already done
      chrome.scripting.executeScript({
        target: { tabId: activeTabId },
        files: ["content.js"]
      }, () => {
        if (chrome.runtime.lastError) {
          alert("Injection failed: " + chrome.runtime.lastError.message + "\n\nNote: You cannot inject overlay scripts on chrome:// pages, extensions pages, or blank new tabs due to Chrome security policy.");
          return;
        }
        
        // Send detection results to content.js to render overlays on page
        chrome.tabs.sendMessage(activeTabId, {
          action: "drawOverlays",
          elements: elements,
          ocr: ocr
        }, (res) => {
          if (chrome.runtime.lastError) {
            console.warn("Message sending failed:", chrome.runtime.lastError.message);
          }
        });
      });
    });
  });
});

// Listener to receive recorded step click messages from content.js overlay
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "recordStep") {
    let actionType = "click";
    let targetText = "";
    let fillValue = null;

    if (request.type === "text") {
      targetText = request.text;
      // Prompt user to see if they want to click or fill this text element
      const response = prompt(`You clicked on text "${targetText}".\n\n- To generate a click: click OK.\n- To type/fill text instead, enter the value below:`);
      if (response === null) {
        sendResponse({ status: "cancelled" });
        return;
      }
      if (response.trim() !== "") {
        actionType = "fill";
        fillValue = response.trim();
      }
    } else if (request.type === "element") {
      // Element boxes detected by YOLO (e.g. input_field, button)
      const isInput = request.label.toLowerCase().includes("input");
      if (isInput) {
        actionType = "fill";
        const val = prompt("You clicked on an input field. Enter the text value to fill:");
        if (val === null) {
          sendResponse({ status: "cancelled" });
          return;
        }
        fillValue = val;
      }
      
      // Request target anchor text to keep script DOM-less
      const anchor = prompt(`You clicked on a UI element [${request.label}].\nProvide an anchor text to locate it (optional):`);
      if (anchor === null) {
        sendResponse({ status: "cancelled" });
        return;
      }
      targetText = anchor.trim() || request.label;
    }

    // Add step to list
    recordedSteps.push({
      action: actionType,
      target: targetText,
      value: fillValue
    });

    // Save state
    chrome.storage.local.set({ recordedSteps: recordedSteps });

    // Update code textarea
    renderStepsList();
    updateScriptOutput();

    sendResponse({ status: "success" });
  }
});

// Hide overlays manually on page
hideOverlaysBtn.addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs.length) {
      chrome.tabs.sendMessage(tabs[0].id, { action: "clearOverlays" }, () => {
        if (chrome.runtime.lastError) {
          console.log("No active overlays to hide (safe to ignore).");
        }
      });
    }
  });
});

langSelect.addEventListener("change", () => {
  chrome.storage.local.set({ selectedLanguage: langSelect.value });
  updateScriptOutput();
});

// Generate automation script in textarea based on selected language
function updateScriptOutput() {
  if (!recordedSteps.length) {
    scriptBox.value = "";
    return;
  }

  const lang = langSelect.value;
  let codeLines = [];

  if (lang === "python_playwright") {
    codeLines.push("# VisiFlow Python Playwright Automation Script");
    codeLines.push("from playwright.sync_api import sync_playwright");
    codeLines.push("from visiflow import VisiPlaywrightPage\n");
    codeLines.push("with sync_playwright() as p:");
    codeLines.push("    browser = p.chromium.launch(headless=False)");
    codeLines.push("    page = browser.new_page()");
    codeLines.push(`    page.goto("${activeTabUrl}")`);
    codeLines.push("    v = VisiPlaywrightPage(page)\n");
    
    recordedSteps.forEach(step => {
      if (step.action === "click") {
        codeLines.push(`    v.visual_click("${step.target}")`);
      } else if (step.action === "fill") {
        codeLines.push(`    v.visual_fill("${step.target}", "${step.value}")`);
      } else if (step.action === "key") {
        codeLines.push(`    v.visual_press("${step.target}")`);
      }
    });
  } else if (lang === "python_selenium") {
    codeLines.push("# VisiFlow Python Selenium Automation Script");
    codeLines.push("from selenium import webdriver");
    codeLines.push("from visiflow import VisiSeleniumDriver\n");
    codeLines.push("driver = webdriver.Chrome()");
    codeLines.push(`driver.get("${activeTabUrl}")`);
    codeLines.push("v = VisiSeleniumDriver(driver)\n");
    
    recordedSteps.forEach(step => {
      if (step.action === "click") {
        codeLines.push(`v.visual_click("${step.target}")`);
      } else if (step.action === "fill") {
        codeLines.push(`v.visual_fill("${step.target}", "${step.value}")`);
      } else if (step.action === "key") {
        codeLines.push(`v.visual_press("${step.target}")`);
      }
    });
  } else if (lang === "js_playwright") {
    codeLines.push("// VisiFlow Node.js Playwright Automation Script");
    codeLines.push("const { chromium } = require('playwright');");
    codeLines.push("const { VisiPage } = require('visiflow-js');\n");
    codeLines.push("(async () => {");
    codeLines.push("    const browser = await chromium.launch({ headless: false });");
    codeLines.push("    const page = await browser.newPage();");
    codeLines.push(`    await page.goto('${activeTabUrl}');`);
    codeLines.push("    const v = new VisiPage(page);\n");
    
    recordedSteps.forEach(step => {
      if (step.action === "click") {
        codeLines.push(`    await v.visualClick('${step.target}');`);
      } else if (step.action === "fill") {
        codeLines.push(`    await v.visualFill('${step.target}', '${step.value}');`);
      } else if (step.action === "key") {
        codeLines.push(`    await v.visualPress('${step.target}');`);
      }
    });
    codeLines.push("\n    await browser.close();");
    codeLines.push("})();");
  }

  scriptBox.value = codeLines.join("\n");
}

// Copy script to clipboard
copyBtn.addEventListener("click", () => {
  if (!scriptBox.value) return;
  scriptBox.select();
  document.execCommand("copy");
  alert("VisiFlow automation script copied to clipboard!");
});

// Clear all steps
clearBtn.addEventListener("click", () => {
  if (confirm("Are you sure you want to clear all recorded steps?")) {
    recordedSteps = [];
    chrome.storage.local.set({ recordedSteps: [] });
    renderStepsList();
    updateScriptOutput();

    // Clear active overlays if any
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs.length) {
        chrome.tabs.sendMessage(tabs[0].id, { action: "clearOverlays" }, () => {
          if (chrome.runtime.lastError) {
            // Safe to ignore if content script is not loaded
          }
        });
      }
    });
  }
});

// Run/Replay Script sequentially in current browser tab
runBtn.addEventListener("click", async () => {
  if (!recordedSteps.length) {
    alert("No steps recorded. Please scan and record some clicks/fills first!");
    return;
  }
  
  runBtn.disabled = true;
  runBtn.textContent = "▶️ Running...";
  scriptBox.value = "// Replaying recorded steps in your browser tab sequentially...";
  
  // Hide active overlays first so they don't block element discovery or clicks
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs.length) {
      chrome.tabs.sendMessage(tabs[0].id, { action: "clearOverlays" }, () => {
        if (chrome.runtime.lastError) {
          // Safe to ignore if content script is not loaded
        }
      });
    }
  });
  
  // Wait a short time for overlays to fade out
  await new Promise(r => setTimeout(r, 200));

  for (let i = 0; i < recordedSteps.length; i++) {
    const step = recordedSteps[i];
    
    if (step.action === "key") {
      scriptBox.value += `\n// [Step ${i+1}/${recordedSteps.length}] Sending keyboard key: "${step.target}"...`;
      
      await new Promise(resolve => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (!tabs.length) {
            resolve();
            return;
          }
          
          chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            files: ["content.js"]
          }, () => {
            if (chrome.runtime.lastError) {
              console.error("Playback injection failed:", chrome.runtime.lastError.message);
              resolve();
              return;
            }
            chrome.tabs.sendMessage(tabs[0].id, {
              action: "executePlayback",
              type: "key",
              x: 0,
              y: 0,
              value: step.target
            }, () => {
              if (chrome.runtime.lastError) {
                console.warn("Playback sendMessage failed:", chrome.runtime.lastError.message);
              }
              resolve();
            });
          });
        });
      });
    } else {
      scriptBox.value += `\n// [Step ${i+1}/${recordedSteps.length}] Finding & executing target: "${step.target}"...`;
      
      // 1. Capture screen and query local match API for coordinates of this text/label
      const res = await new Promise(resolve => {
        chrome.runtime.sendMessage({ action: "resolveTarget", query: step.target }, resolve);
      });
      
      if (!res || !res.found) {
        alert(`Playback failed at step ${i+1}: Could not visually find target "${step.target}" on page.`);
        break;
      }
      
      // 2. Dispatch simulated click or fill event to content.js
      const dpr = window.devicePixelRatio || 1;
      await new Promise(resolve => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
          if (!tabs.length) {
            resolve();
            return;
          }
          
          chrome.scripting.executeScript({
            target: { tabId: tabs[0].id },
            files: ["content.js"]
          }, () => {
            if (chrome.runtime.lastError) {
              console.error("Playback injection failed:", chrome.runtime.lastError.message);
              resolve();
              return;
            }
            chrome.tabs.sendMessage(tabs[0].id, {
              action: "executePlayback",
              type: step.action,
              x: res.x / dpr,
              y: res.y / dpr,
              value: step.value
            }, () => {
              if (chrome.runtime.lastError) {
                console.warn("Playback sendMessage failed:", chrome.runtime.lastError.message);
              }
              resolve();
            });
          });
        });
      });
    }
    
    // 3. Wait for layout changes, page load, or transitions before doing next step
    await new Promise(resolve => setTimeout(resolve, 1800));
  }
  
  runBtn.disabled = false;
  runBtn.textContent = "▶️ Run Script";
  renderStepsList();
  updateScriptOutput();
});
