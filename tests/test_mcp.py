import sys
import json
import unittest
from pathlib import Path
from io import StringIO
from unittest.mock import patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from visiflow.mcp import VisiFlowMCPServer

class TestVisiFlowMCP(unittest.TestCase):
    def test_mcp_initialize_and_tools_list(self):
        server = VisiFlowMCPServer()
        tools = server._get_tools_schema()
        tool_names = [t["name"] for t in tools]
        
        self.assertIn("visiflow_navigate", tool_names)
        self.assertIn("visiflow_click", tool_names)
        self.assertIn("visiflow_fill", tool_names)
        self.assertIn("visiflow_press", tool_names)
        self.assertIn("visiflow_assert", tool_names)
        self.assertIn("visiflow_screenshot", tool_names)
        self.assertIn("visiflow_close", tool_names)
        print("\n[PASS] Verified all 7 MCP tools schemas are correctly defined.")

    def test_mcp_json_rpc_loop(self):
        input_messages = [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            json.dumps({"jsonrpc": "2.0", "id": 3, "method": "ping"})
        ]
        input_data = "\n".join(input_messages) + "\n"

        output_buffer = StringIO()

        with patch("sys.stdin", StringIO(input_data)), patch("sys.stdout", output_buffer):
            server = VisiFlowMCPServer()
            server.run()

        output_lines = [line for line in output_buffer.getvalue().strip().split("\n") if line]
        self.assertEqual(len(output_lines), 3) # initialize, tools/list, ping responses

        init_resp = json.loads(output_lines[0])
        self.assertEqual(init_resp["id"], 1)
        self.assertEqual(init_resp["result"]["serverInfo"]["name"], "visiflow-mcp")

        tools_resp = json.loads(output_lines[1])
        self.assertEqual(tools_resp["id"], 2)
        self.assertGreaterEqual(len(tools_resp["result"]["tools"]), 7)

        ping_resp = json.loads(output_lines[2])
        self.assertEqual(ping_resp["id"], 3)
        print("[PASS] Verified MCP JSON-RPC stdio server responds properly to initialize, tools/list, and ping.")

if __name__ == "__main__":
    unittest.main()
