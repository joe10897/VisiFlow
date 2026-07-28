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
    
    if (type === "key") {
      // Keyboard action: target is the active element (e.g. focused search input)
      const target = document.activeElement || document.body;
      const keyName = value || "Enter";
      const cleanKey = keyName.replace(/[{}]/g, "");
      const titleKey = cleanKey.charAt(0).toUpperCase() + cleanKey.slice(1); // e.g. "Enter"
      
      // Calculate viewport coordinate for active element to show visual indicator
      const rect = target.getBoundingClientRect();
      const scrollX = window.scrollX || window.pageXOffset;
      const scrollY = window.scrollY || window.pageYOffset;
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      
      // Play indicator & border glow
      showPlaybackIndicator(cx + scrollX, cy + scrollY, "key");
      showPlaybackBorderHighlight(target, "key");
      
      // Dispatch key events
      setTimeout(() => {
        target.dispatchEvent(new KeyboardEvent("keydown", { key: titleKey, code: titleKey, bubbles: true, cancelable: true }));
        target.dispatchEvent(new KeyboardEvent("keypress", { key: titleKey, code: titleKey, bubbles: true, cancelable: true }));
        
        // Custom behavior for Enter to submit form if applicable
        if (titleKey === "Enter") {
          if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
            const form = target.form;
            if (form) {
              form.submit();
            } else {
              // Pressing enter on Google search input triggers a click on search button or submit action
              // Fallback: send input event
              target.dispatchEvent(new Event("change", { bubbles: true }));
            }
          }
        }
        
        target.dispatchEvent(new KeyboardEvent("keyup", { key: titleKey, code: titleKey, bubbles: true, cancelable: true }));
      }, 200);
      
      sendResponse({ status: "success" });
      return;
    }

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
      const closestInteractive = target.closest("a, button, input, textarea, [role='button'], [role='combobox'], [role='searchbox']");
      if (closestInteractive) {
        target = closestInteractive;
      }
    }

    // Play beautiful pulse circle animation at coordinate
    showPlaybackIndicator(absoluteX, absoluteY, type);
    
    // Highlight the target element with a temporary border highlight glow
    if (target) {
      showPlaybackBorderHighlight(target, type);
    }

    setTimeout(() => {
      if (type === "click") {
        if (target) {
          if (typeof target.focus === "function") target.focus();
          target.click();
          target.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
        }
      } else if (type === "fill") {
        // Walk DOM to find the real input element (handles wrapper divs, React, etc.)
        function findInputEl(el) {
          if (!el) return null;
          // Direct input/textarea
          if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") return el;
          // ARIA searchbox / combobox (Google search bar)
          if (el.getAttribute("role") === "combobox" || el.getAttribute("role") === "searchbox") return el;
          // Search within children
          const inner = el.querySelector("input, textarea, [role='combobox'], [role='searchbox']");
          if (inner) return inner;
          // Walk up the DOM tree up to 5 levels
          let parent = el.parentElement;
          for (let i = 0; i < 5 && parent; i++, parent = parent.parentElement) {
            const found = parent.querySelector("input, textarea, [role='combobox'], [role='searchbox']");
            if (found) return found;
          }
          return null;
        }
        
        const inputEl = findInputEl(target);
        
        if (inputEl) {
          inputEl.focus();
          inputEl.click();
          
          // --- React-compatible value setter ---
          // React overrides the native .value setter with a custom one.
          // To bypass it, we call the ORIGINAL native setter via Object.getOwnPropertyDescriptor.
          const nativeInputProto = Object.getPrototypeOf(inputEl);
          const descriptor = Object.getOwnPropertyDescriptor(nativeInputProto, "value");
          if (descriptor && descriptor.set) {
            descriptor.set.call(inputEl, value);
          } else {
            inputEl.value = value;
          }
          
          // Fire all the events React/Vue/Angular expect for a controlled input
          const events = [
            new Event("input", { bubbles: true }),
            new Event("change", { bubbles: true }),
            new KeyboardEvent("keydown", { bubbles: true, key: "a" }),
            new KeyboardEvent("keypress", { bubbles: true, key: "a" }),
            new KeyboardEvent("keyup", { bubbles: true, key: "a" }),
          ];
          events.forEach(e => inputEl.dispatchEvent(e));
          
          // Simulate typing each character for frameworks that listen to keyboard events
          setTimeout(() => {
            for (const char of value) {
              inputEl.dispatchEvent(new KeyboardEvent("keydown",  { key: char, bubbles: true }));
              inputEl.dispatchEvent(new KeyboardEvent("keypress", { key: char, bubbles: true }));
              inputEl.dispatchEvent(new KeyboardEvent("keyup",    { key: char, bubbles: true }));
            }
          }, 50);
        } else {
          // Last resort: click and use execCommand to insert text
          if (target) {
            target.focus();
            document.execCommand("insertText", false, value);
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
  const color = type === "click" ? "#f43f5e" : (type === "key" ? "#10b981" : "#38bdf8");
  const colorAlpha = type === "click" ? "rgba(244, 63, 94, 0.4)" : (type === "key" ? "rgba(16, 185, 129, 0.4)" : "rgba(56, 189, 248, 0.4)");
  let label = "🖱 Click";
  if (type === "fill") label = "⌨️ Fill";
  else if (type === "key") label = "⌨️ Key";

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

function showPlaybackBorderHighlight(target, type) {
  if (!target) return;
  const rect = target.getBoundingClientRect();
  const scrollX = window.scrollX || window.pageXOffset;
  const scrollY = window.scrollY || window.pageYOffset;
  
  const borderHighlight = document.createElement("div");
  const color = type === "click" ? "#f43f5e" : (type === "key" ? "#10b981" : "#38bdf8");
  
  borderHighlight.style.cssText = `
    position: absolute;
    left: ${rect.left + scrollX}px;
    top: ${rect.top + scrollY}px;
    width: ${rect.width}px;
    height: ${rect.height}px;
    border: 3px solid ${color};
    box-shadow: 0 0 20px ${color}, inset 0 0 10px ${color};
    border-radius: 6px;
    z-index: 2147483646;
    pointer-events: none;
    opacity: 0;
    transform: scale(1.03);
    transition: opacity 0.25s ease, transform 0.25s ease;
  `;
  document.body.appendChild(borderHighlight);
  
  // Trigger entry animation
  requestAnimationFrame(() => {
    borderHighlight.style.opacity = "1";
    borderHighlight.style.transform = "scale(1)";
  });
  
  // Fade out and remove
  setTimeout(() => {
    borderHighlight.style.opacity = "0";
    borderHighlight.style.transform = "scale(0.97)";
    setTimeout(() => borderHighlight.remove(), 250);
  }, 900);
}


