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
    
    // Draw YOLO elements (Cyan boxes)
    elements.forEach(elem => {
      const [x1, y1, x2, y2] = elem.box;
      createOverlayBox(container, x1, y1, x2 - x1, y2 - y1, "#38bdf8", "rgba(56, 189, 248, 0.15)", () => {
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
      createOverlayBox(container, x1, y1, x2 - x1, y2 - y1, "#34d399", "rgba(52, 211, 153, 0.2)", () => {
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
