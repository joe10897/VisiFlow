// Background service worker for VisiFlow Chrome Extension

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "captureAndDetect") {
    // Capture the visible area of the active tab
    chrome.tabs.captureVisibleTab(null, { format: "png" }, (dataUrl) => {
      if (chrome.runtime.lastError || !dataUrl) {
        sendResponse({ status: "error", message: "Failed to capture screenshot: " + (chrome.runtime.lastError ? chrome.runtime.lastError.message : "") });
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
        if (!resp.ok) throw new Error("Local VisiFlow server returned HTTP " + resp.status);
        return resp.json();
      })
      .then(data => {
        sendResponse({ status: "success", data: data, screenshot: dataUrl });
      })
      .catch(err => {
        console.error("VisiFlow Server Connection Error:", err);
        sendResponse({ status: "error", message: "VisiFlow server connection failed: " + err.message });
      });
    });
    return true; // Keep message channel open for asynchronous response
  }
});
