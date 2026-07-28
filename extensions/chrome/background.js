// Background service worker for VisiFlow Chrome Extension

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "captureAndDetect") {
    // Query active tab to determine the correct windowId (avoids capturing popup window)
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (chrome.runtime.lastError || !tabs || !tabs.length) {
        sendResponse({ status: "error", message: "No active tab found: " + (chrome.runtime.lastError ? chrome.runtime.lastError.message : "") });
        return;
      }
      
      const windowId = tabs[0].windowId;
      
      try {
        chrome.tabs.captureVisibleTab(windowId, { format: "png" }, (dataUrl) => {
          try {
            if (chrome.runtime.lastError || !dataUrl) {
              const errorMsg = chrome.runtime.lastError ? chrome.runtime.lastError.message : "Failed to capture screenshot.";
              sendResponse({ status: "error", message: errorMsg });
              return;
            }

            // Send the screenshot to the local VisiFlow FastAPI daemon
            const formData = new FormData();
            formData.append("image_base64", dataUrl);

            fetch("http://localhost:8000/detect", {
              method: "POST",
              body: formData
            })
            .then(resp => {
              if (!resp.ok) {
                return resp.text().then(text => {
                  throw new Error(`Server HTTP ${resp.status}: ${text || "Internal Server Error"}`);
                });
              }
              return resp.json();
            })
            .then(data => {
              sendResponse({ status: "success", data: data, screenshot: dataUrl });
            })
            .catch(err => {
              console.error("VisiFlow Server Connection Error:", err);
              sendResponse({ status: "error", message: "VisiFlow server connection failed: " + err.message });
            });
          } catch (innerErr) {
            sendResponse({ status: "error", message: "Background callback exception: " + innerErr.message });
          }
        });
      } catch (err) {
        sendResponse({ status: "error", message: "Chrome API exception: " + err.message });
      }
    });
    return true; // Keep message channel open for asynchronous response
  }
});

// Configure the side panel to open when clicking the extension icon in the toolbar
chrome.sidePanel
  .setPanelBehavior({ openPanelOnActionClick: true })
  .catch((error) => console.error("Error setting side panel behavior:", error));
