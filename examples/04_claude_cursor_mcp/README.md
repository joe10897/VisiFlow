# VisiFlow MCP Server for Claude Desktop & Cursor

This example shows how to equip LLM AI Agents (Anthropic Claude Desktop, Cursor AI, Windsurf) with visual browser automation using the **Model Context Protocol (MCP)**.

## Why VisiFlow MCP?

- **$0 LLM Token Cost**: Coordinates and element recognition run 100% locally via YOLO and EasyOCR on CPU. No costly vision API calls required.
- **Zero DOM Brittle Selectors**: The Agent navigates purely by visible labels and spatial cues (e.g. `click 'Delete' right of 'Alice'`).
- **100% Offline & Private**: No web page screenshots leave your machine.

## Setup Instructions

### 1. Claude Desktop
Add this to your Claude Desktop configuration file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "visiflow": {
      "command": "visiflow",
      "args": ["mcp"]
    }
  }
}
```

### 2. Cursor IDE
Create or edit `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "visiflow": {
      "command": "visiflow",
      "args": ["mcp"]
    }
  }
}
```

## Example Prompts to Give to Your Agent

Once connected, you can simply ask Claude or Cursor in natural language:

> *"Open https://github.com/login, fill the username field with 'my_username', fill the password with 'secret', and visually click 'Sign in'."*

> *"Navigate to the user table at http://localhost:8000/users, find the row with 'Alice Smith', and click the 'Delete' button to the right of her name."*
