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
    let element = document.elementFromPoint(x, y);
    
    // Resolve clickable/focusable target element hierarchy
    let target = element;
    if (target) {
      const closestInteractive = target.closest("a, button, input, textarea, [role='button']");
      if (closestInteractive) {
        target = closestInteractive;
      }
    }

    // Play beautiful pulse circle animation at coordinate
    showPlaybackIndicator(absoluteX, absoluteY, type);
    
    // Highlight the target element with a temporary glow
    if (target) {
      const originalOutline = target.style.outline;
      const originalTransition = target.style.transition;
      target.style.transition = "outline 0.2s ease, box-shadow 0.2s ease";
      target.style.outline = type === "click" ? "3px solid #f43f5e" : "3px solid #38bdf8";
      target.style.boxShadow = type === "click" ? "0 0 10px rgba(244, 63, 94, 0.6)" : "0 0 10px rgba(56, 189, 248, 0.6)";
      setTimeout(() => {
        target.style.outline = originalOutline;
        target.style.boxShadow = "";
        setTimeout(() => {
          target.style.transition = originalTransition;
        }, 200);
      }, 800);
    }

    setTimeout(() => {
      if (type === "click") {
        if (target) {
          // Focus element first
          if (typeof target.focus === "function") {
            target.focus();
          }
          target.click();
          target.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
        }
      } else if (type === "fill") {
        if (target) {
          let inputEl = target;
          if (inputEl.tagName !== "INPUT" && inputEl.tagName !== "TEXTAREA") {
            inputEl = target.querySelector("input, textarea") || target.closest("input, textarea");
            if (!inputEl) {
              const parent = target.parentElement;
              if (parent) {
                inputEl = parent.querySelector("input, textarea");
              }
            }
          }
          if (inputEl) {
            inputEl.focus();
            inputEl.value = value;
            inputEl.dispatchEvent(new Event("input", { bubbles: true }));
            inputEl.dispatchEvent(new Event("change", { bubbles: true }));
          } else {
            target.focus();
            target.innerText = value;
            target.dispatchEvent(new Event("input", { bubbles: true }));
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
  const color = type === "click" ? "#f43f5e" : "#38bdf8";
  const colorAlpha = type === "click" ? "rgba(244, 63, 94, 0.4)" : "rgba(56, 189, 248, 0.4)";
  const label = type === "click" ? "🖱 Click" : "⌨️ Fill";

  // ── Outer ripple ring ──────────────────────────────────────
  const ring = document.createElement("div");
  ring.style.cssText = `
    position: fixed;
    left: ${x - 28}px;
    top: ${y - 28}px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    border: 2px solid ${color};
    background: transparent;
    z-index: 2147483647;
    pointer-events: none;
    opacity: 1;
    transform: scale(0.3);
    transition: transform 0.55s cubic-bezier(0.1, 0.8, 0.3, 1), opacity 0.55s ease-out;
  `;
  document.body.appendChild(ring);

  // ── Inner filled pulse dot ─────────────────────────────────
  const dot = document.createElement("div");
  dot.style.cssText = `
    position: fixed;
    left: ${x - 16}px;
    top: ${y - 16}px;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: ${colorAlpha};
    border: 2.5px solid ${color};
    z-index: 2147483647;
    pointer-events: none;
    opacity: 1;
    transform: scale(0.4);
    transition: transform 0.4s cubic-bezier(0.1, 0.8, 0.3, 1), opacity 0.4s ease-out;
    box-shadow: 0 0 16px ${color};
  `;
  document.body.appendChild(dot);

  // ── Action label badge ─────────────────────────────────────
  const badge = document.createElement("div");
  badge.style.cssText = `
    position: fixed;
    left: ${x + 20}px;
    top: ${y - 14}px;
    background: ${color};
    color: white;
    font-size: 11px;
    font-weight: 700;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    padding: 3px 8px;
    border-radius: 6px;
    z-index: 2147483647;
    pointer-events: none;
    opacity: 0;
    transform: translateX(-6px);
    transition: opacity 0.2s ease, transform 0.2s ease;
    white-space: nowrap;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3);
  `;
  badge.textContent = label;
  document.body.appendChild(badge);

  // Animate in on next frame
  requestAnimationFrame(() => {
    ring.style.transform = "scale(1.6)";
    ring.style.opacity = "0";
    dot.style.transform = "scale(1)";
    badge.style.opacity = "1";
    badge.style.transform = "translateX(0)";
  });

  // Fade out and remove
  setTimeout(() => {
    dot.style.opacity = "0";
    badge.style.opacity = "0";
    setTimeout(() => {
      ring.remove();
      dot.remove();
      badge.remove();
    }, 450);
  }, 700);
}

