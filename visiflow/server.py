import os
import tempfile
import base64
import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from fastapi.staticfiles import StaticFiles
from .core import VisiFlowDetector, logger

app = FastAPI(title="VisiFlow Vision Daemon", version="0.1.0")

# Mount static files directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/ui/static", StaticFiles(directory=static_dir), name="ui-static")

# Enable CORS for local cross-origin queries (e.g. from browser playground)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global lazy-initialized detector
detector_instance: Optional[VisiFlowDetector] = None

def get_detector() -> VisiFlowDetector:
    global detector_instance
    if detector_instance is None:
        logger.info("Initializing global VisiFlowDetector instance for HTTP server...")
        # Use YOLO with fallback
        detector_instance = VisiFlowDetector(use_yolo=True)
    return detector_instance

class Base64MatchRequest(BaseModel):
    image_base64: str
    query: str
    fuzzy_threshold: Optional[float] = 0.6

@app.get("/")
def read_root():
    return {"status": "ok", "service": "VisiFlow Vision Daemon", "version": "0.1.0"}

@app.post("/match")
async def match_target(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None),
    query: str = Form(...)
):
    """
    Match a target query string against a screenshot image and return the resolved viewport coordinates.
    Accepts either file upload or base64 encoded image string.
    """
    detector = get_detector()
    
    # Save image bytes to temp file
    fd, temp_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    
    try:
        if file:
            content = await file.read()
            with open(temp_path, "wb") as f:
                f.write(content)
        elif image_base64:
            # Clean base64 prefix if present
            if "," in image_base64:
                image_base64 = image_base64.split(",")[1]
            img_bytes = base64.b64decode(image_base64)
            with open(temp_path, "wb") as f:
                f.write(img_bytes)
        else:
            raise HTTPException(status_code=400, detail="Either 'file' or 'image_base64' must be provided.")
            
        coords = detector.find_element_by_text(temp_path, query)
        if coords:
            return {"found": True, "x": coords[0], "y": coords[1], "query": query}
        return {"found": False, "x": None, "y": None, "query": query}
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/detect")
async def detect_all(
    file: Optional[UploadFile] = File(None),
    image_base64: Optional[str] = Form(None)
):
    """
    Detect all UI element bounding boxes and OCR texts for the Web Playground.
    """
    detector = get_detector()
    
    fd, temp_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    
    try:
        if file:
            content = await file.read()
            with open(temp_path, "wb") as f:
                f.write(content)
        elif image_base64:
            if "," in image_base64:
                image_base64 = image_base64.split(",")[1]
            img_bytes = base64.b64decode(image_base64)
            with open(temp_path, "wb") as f:
                f.write(img_bytes)
        else:
            raise HTTPException(status_code=400, detail="Either 'file' or 'image_base64' must be provided.")
            
        elements = detector.detect_elements(temp_path)
        ocr_items = detector.run_ocr(temp_path)
        
        return {
            "status": "success",
            "elements": elements,
            "ocr": ocr_items
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.post("/detect_url")
async def detect_url(
    url: str = Form(...)
):
    """
    Launch Playwright, navigate to the URL, capture screenshot,
    and run detection/OCR on it.
    """
    detector = get_detector()
    
    fd, temp_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise HTTPException(
            status_code=400, 
            detail="Playwright is required to use URL visualization. Run 'pip install playwright && playwright install' first."
        )
        
    try:
        logger.info(f"Navigating to URL to capture screenshot: {url}")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1280, "height": 800})
            
            # Navigate to URL and wait for network to settle (essential for SPAs / dynamic APIs)
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Wait an additional 2 seconds to allow animations/JS rendering to settle
            await page.wait_for_timeout(2000)
            
            # Take normal viewport screenshot
            await page.screenshot(path=temp_path)
            await browser.close()
            
        elements = detector.detect_elements(temp_path)
        ocr_items = detector.run_ocr(temp_path)
        
        with open(temp_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode("utf-8")
            
        return {
            "status": "success",
            "image_base64": f"data:image/png;base64,{encoded_string}",
            "elements": elements,
            "ocr": ocr_items
        }
    except Exception as e:
        logger.error(f"Error rendering URL: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load URL: {str(e)}")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

class StepModel(BaseModel):
    action: str
    target: str
    value: Optional[str] = None

class RunScriptRequest(BaseModel):
    url: str
    steps: List[StepModel]

@app.post("/run_script")
async def run_script(req: RunScriptRequest):
    """
    Launch a local browser (headless=False) to run/replay the recorded steps.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        raise HTTPException(
            status_code=400, 
            detail="Playwright is required to run scripts. Run 'pip install playwright && playwright install' first."
        )
    
    logger.info(f"Replaying {len(req.steps)} steps on: {req.url}")
    try:
        async with async_playwright() as p:
            # Open visible browser so the user can see the playback magic!
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1280, "height": 800})
            
            # Navigate to URL
            await page.goto(req.url, wait_until="networkidle", timeout=30000)
            
            detector = get_detector()
            
            for idx, step in enumerate(req.steps):
                logger.info(f"Executing step {idx+1}/{len(req.steps)}: {step.action} on '{step.target}'")
                
                if step.action == "key":
                    clean_key = step.target.strip("{}")
                    title_key = clean_key.capitalize() if clean_key.lower() in ["enter", "tab", "escape", "backspace"] else clean_key
                    await page.keyboard.press(title_key)
                    await page.wait_for_timeout(1200)
                    continue
                
                # Click/Fill coordinate resolution
                fd, temp_path = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                try:
                    await page.screenshot(path=temp_path)
                    img = cv2.imread(temp_path)
                    if img is None:
                        raise Exception("Failed to read browser screenshot")
                    sh, sw = img.shape[:2]
                    
                    viewport = page.viewport_size
                    scale_x = viewport["width"] / sw
                    scale_y = viewport["height"] / sh
                    
                    coords = detector.find_element_by_text(temp_path, step.target)
                    if not coords:
                        raise Exception(f"Could not visually find target '{step.target}' on page.")
                    
                    px = int(coords[0] * scale_x)
                    py = int(coords[1] * scale_y)
                    
                    if step.action == "click":
                        await page.mouse.click(px, py)
                    elif step.action == "fill":
                        await page.mouse.click(px, py, click_count=3)
                        await page.keyboard.press("Backspace")
                        await page.keyboard.type(step.value or "")
                        
                    await page.wait_for_timeout(1500)
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            
            # Settle wait before close
            await page.wait_for_timeout(2500)
            await browser.close()
            
        return {"status": "success", "message": "Replay finished successfully"}
    except Exception as e:
        logger.error(f"Error during script replay: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/ui", response_class=HTMLResponse)
def get_web_ui():
    """
    Serve the Web Playground static HTML UI.
    """
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    html_path = os.path.join(static_dir, "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return HTMLResponse("<h1>VisiFlow Web Playground</h1><p>Static UI not found.</p>")
