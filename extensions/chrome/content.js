// Content script to draw interactive VisiFlow overlays on top of the live web page

let activeOverlays = [];

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "drawOverlays") {
    clearOverlays();
    
    const elements = request.elements || [];
    const ocr = request.ocr || [];
    
    // Create an overlay layer container appended to document body
    const container = document.createElement("div");
    container.id = "visiflow-overlay-container";
    container.style.cssText = `
      position: absolute;
      top: 0; left: 0; width: 100%; height: 100%;
      pointer-events: none;
      z-index: 2147483647;
    `;
    document.body.appendChild(container);
    activeOverlays.push(container);
    
    const dpr = window.devicePixelRatio || 1;
    
    // Draw YOLO elements (Cyan boxes)
    elements.forEach(elem => {
      const [x1, y1, x2, y2] = elem.box;
      createOverlayBox(container, x1 / dpr, y1 / dpr, (x2 - x1) / dpr, (y2 - y1) / dpr, "#38bdf8", "rgba(56, 189, 248, 0.15)", () => {
        chrome.runtime.sendMessage({
          action: "recordStep",
          type: "element",
          label: elem.label,
          box: elem.box
        });
      });
    });
    
    // Draw OCR elements (Emerald boxes)
    ocr.forEach(item => {
      const [x1, y1, x2, y2] = item.box;
      createOverlayBox(container, x1 / dpr, y1 / dpr, (x2 - x1) / dpr, (y2 - y1) / dpr, "#34d399", "rgba(52, 211, 153, 0.2)", () => {
        chrome.runtime.sendMessage({
          action: "recordStep",
          type: "text",
          text: item.text,
          box: item.box
        });
      });
    });
    
    sendResponse({ status: "success" });
  } else if (request.action === "clearOverlays") {
    clearOverlays();
    sendResponse({ status: "success" });
  } else if (request.action === "executePlayback") {
    const { type, x, y, value } = request;
    const scrollX = window.scrollX || window.pageXOffset;
    const scrollY = window.scrollY || window.pageYOffset;
    
    // Calculate absolute positions matching page scrolls
    const absoluteX = x + scrollX;
    const absoluteY = y + scrollY;
    
    // Retrieve DOM element at targeted client coordinate
    const element = document.elementFromPoint(x, y);
    
    // Play beautiful pulse circle animation at coordinate
    showPlaybackIndicator(absoluteX, absoluteY, type);
    
    setTimeout(() => {
      if (type === "click") {
        if (element) {
          element.click();
          element.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
        }
      } else if (type === "fill") {
        if (element) {
          let inputEl = element;
          if (inputEl.tagName !== "INPUT" && inputEl.tagName !== "TEXTAREA") {
            inputEl = element.querySelector("input, textarea") || element.closest("input, textarea");
          }
          if (inputEl) {
            inputEl.value = value;
            inputEl.dispatchEvent(new Event("input", { bubbles: true }));
            inputEl.dispatchEvent(new Event("change", { bubbles: true }));
          } else {
            element.innerText = value;
            element.dispatchEvent(new Event("input", { bubbles: true }));
          }
        }
      }
    }, 450);
    
    sendResponse({ status: "success" });
  }
});

function createOverlayBox(parent, x, y, w, h, borderCol, fillCol, onClick) {
  const box = document.createElement("div");
  // Adjust for current window scroll offsets because coordinates are viewport-relative
  const scrollX = window.scrollX || window.pageXOffset;
  const scrollY = window.scrollY || window.pageYOffset;
  
  box.style.cssText = `
    position: absolute;
    left: ${x + scrollX}px;
    top: ${y + scrollY}px;
    width: ${w}px;
    height: ${h}px;
    border: 2px solid ${borderCol};
    background-color: ${fillCol};
    cursor: pointer;
    pointer-events: auto;
    transition: background-color 0.2s;
    box-sizing: border-box;
  `;
  
  box.addEventListener("mouseenter", () => {
    box.style.backgroundColor = borderCol + "44"; // Brighter fill on hover
  });
  box.addEventListener("mouseleave", () => {
    box.style.backgroundColor = fillCol;
  });
  box.addEventListener("click", (e) => {
    e.preventDefault();
    e.stopPropagation();
    onClick();
  });
  
  parent.appendChild(box);
}

function clearOverlays() {
  const container = document.getElementById("visiflow-overlay-container");
  if (container) container.remove();
  activeOverlays = [];
}

function showPlaybackIndicator(x, y, type) {
  const pulse = document.createElement("div");
  pulse.style.cssText = `
    position: absolute;
    left: ${x - 20}px;
    top: ${y - 20}px;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    border: 3px solid ${type === "click" ? "#f43f5e" : "#38bdf8"};
    background-color: ${type === "click" ? "rgba(244, 63, 94, 0.35)" : "rgba(56, 189, 248, 0.35)"};
    z-index: 2147483647;
    pointer-events: none;
    transition: transform 0.4s cubic-bezier(0.1, 0.8, 0.3, 1), opacity 0.4s ease-out;
    transform: scale(0.4);
    opacity: 1;
  `;
  document.body.appendChild(pulse);
  
  // Trigger expanding ripple pulse animation
  requestAnimationFrame(() => {
    pulse.style.transform = "scale(1.3)";
  });
  
  setTimeout(() => {
    pulse.style.opacity = "0";
    setTimeout(() => pulse.remove(), 400);
  }, 500);
}
