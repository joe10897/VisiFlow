import sys
import json
import os
import tempfile
import traceback
from typing import Dict, Any, Optional

class VisiFlowMCPServer:
    """
    Standard Model Context Protocol (MCP) Stdio JSON-RPC Server for VisiFlow.
    Allows Claude Desktop, Cursor, Gemini, and AI Agents to visually control
    browsers locally with $0 token cost and sub-second latency.
    """
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.visipage = None
        self.detector = None

    def _ensure_browser(self, headless: bool = False):
        if self.page is None:
            from playwright.sync_api import sync_playwright
            from .core import VisiFlowDetector
            from .playwright import VisiPlaywrightPage

            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=headless)
            context = self.browser.new_context(viewport={"width": 1280, "height": 800})
            self.page = context.new_page()
            self.detector = VisiFlowDetector()
            self.visipage = VisiPlaywrightPage(self.page, detector=self.detector)

    def _get_tools_schema(self) -> list:
        return [
            {
                "name": "visiflow_navigate",
                "description": "Navigate the browser to a URL and wait for page to render visually.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to navigate to (e.g. 'https://github.com')"},
                        "headless": {"type": "boolean", "description": "Whether to run browser in headless mode (default: false)", "default": False}
                    },
                    "required": ["url"]
                }
            },
            {
                "name": "visiflow_click",
                "description": "Visually locate an element by visible text label (with optional spatial relative constraints) and click it.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "The visible text of the element to click (e.g. 'Submit', 'Delete', 'Sign In')"},
                        "right_of": {"type": "string", "description": "Optional text label of an anchor element to the left of the target (e.g. 'Alice')"},
                        "left_of": {"type": "string", "description": "Optional text label of an anchor element to the right of the target"},
                        "below": {"type": "string", "description": "Optional text label of an anchor element above the target"},
                        "above": {"type": "string", "description": "Optional text label of an anchor element below the target"},
                        "index": {"type": "integer", "description": "Optional 0-based ordinal index among multiple matching candidates"}
                    },
                    "required": ["target"]
                }
            },
            {
                "name": "visiflow_fill",
                "description": "Visually locate an input field by its visible label or placeholder (with optional spatial constraints) and type text into it.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "The visible label or placeholder near the input box (e.g. 'Username', 'Search')"},
                        "value": {"type": "string", "description": "The text string to type into the input field"},
                        "right_of": {"type": "string", "description": "Optional anchor text to the left of the input"},
                        "below": {"type": "string", "description": "Optional anchor text above the input"},
                        "index": {"type": "integer", "description": "Optional 0-based ordinal index among multiple matches"}
                    },
                    "required": ["target", "value"]
                }
            },
            {
                "name": "visiflow_press",
                "description": "Press a keyboard key on the active/focused element (e.g. 'Enter', 'Tab', 'Escape', 'Backspace').",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Key name (e.g. 'Enter', 'Tab', 'Escape', 'Backspace')"}
                    },
                    "required": ["key"]
                }
            },
            {
                "name": "visiflow_assert",
                "description": "Assert that a given text or message is visually visible on screen.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string", "description": "Text that must be visible on the screen"},
                        "timeout_ms": {"type": "integer", "description": "Max timeout in milliseconds (default: 5000)", "default": 5000}
                    },
                    "required": ["target"]
                }
            },
            {
                "name": "visiflow_screenshot",
                "description": "Capture the current browser viewport screenshot and return the saved path.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "visiflow_close",
                "description": "Close the active browser session.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]

    def handle_tool_call(self, name: str, args: Dict[str, Any]) -> str:
        try:
            if name == "visiflow_navigate":
                url = args["url"]
                headless = args.get("headless", False)
                self._ensure_browser(headless=headless)
                self.page.goto(url, wait_until="networkidle", timeout=30000)
                return f"Successfully navigated to {url}"

            elif name == "visiflow_click":
                self._ensure_browser()
                target = args["target"]
                right_of = args.get("right_of")
                left_of = args.get("left_of")
                below = args.get("below")
                above = args.get("above")
                index = args.get("index")
                self.visipage.visual_click(
                    target,
                    right_of=right_of,
                    left_of=left_of,
                    below=below,
                    above=above,
                    index=index,
                    timeout_ms=10000
                )
                return f"Successfully visually clicked on '{target}'"

            elif name == "visiflow_fill":
                self._ensure_browser()
                target = args["target"]
                value = args["value"]
                right_of = args.get("right_of")
                below = args.get("below")
                index = args.get("index")
                self.visipage.visual_fill(
                    target,
                    value,
                    right_of=right_of,
                    below=below,
                    index=index,
                    timeout_ms=10000
                )
                return f"Successfully visually filled '{target}' with value '{value}'"

            elif name == "visiflow_press":
                self._ensure_browser()
                key = args["key"]
                self.visipage.visual_press(key)
                return f"Successfully pressed key '{key}'"

            elif name == "visiflow_assert":
                self._ensure_browser()
                target = args["target"]
                timeout_ms = args.get("timeout_ms", 5000)
                self.visipage.visual_assert_visible(target, timeout_ms=timeout_ms)
                return f"Assertion PASSED: '{target}' is visible on screen."

            elif name == "visiflow_screenshot":
                self._ensure_browser()
                fd, path = tempfile.mkstemp(suffix=".png")
                os.close(fd)
                self.page.screenshot(path=path)
                return f"Screenshot saved to {path}"

            elif name == "visiflow_close":
                if self.browser:
                    self.browser.close()
                    self.browser = None
                if self.playwright:
                    self.playwright.stop()
                    self.playwright = None
                self.page = None
                self.visipage = None
                return "Browser session closed successfully."

            else:
                raise ValueError(f"Unknown tool name: {name}")

        except Exception as e:
            return f"Error executing {name}: {str(e)}"

    def run(self):
        """
        Main Stdio loop processing MCP JSON-RPC 2.0 messages.
        """
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception:
                continue

            msg_id = msg.get("id")
            method = msg.get("method")
            params = msg.get("params", {})

            # Notification (no response)
            if method == "notifications/initialized":
                continue

            if method == "initialize":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "visiflow-mcp",
                            "version": "0.9.0"
                        }
                    }
                }
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            elif method == "tools/list":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "tools": self._get_tools_schema()
                    }
                }
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            elif method == "tools/call":
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                result_text = self.handle_tool_call(tool_name, tool_args)
                is_error = "Error executing" in result_text
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": result_text
                            }
                        ],
                        "isError": is_error
                    }
                }
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            elif method == "ping":
                response = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {}
                }
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()

            else:
                if msg_id is not None:
                    response = {
                        "jsonrpc": "2.0",
                        "id": msg_id,
                        "error": {
                            "code": -32601,
                            "message": f"Method not found: {method}"
                        }
                    }
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()

def start_mcp_server():
    server = VisiFlowMCPServer()
    server.run()

if __name__ == "__main__":
    start_mcp_server()
