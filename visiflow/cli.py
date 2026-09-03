import argparse
import sys
import webbrowser
from pathlib import Path

from .core import VisiFlowDetector, logger

def main():
    parser = argparse.ArgumentParser(
        prog="visiflow",
        description="VisiFlow: Fast, local visual-driven E2E automation testing tool."
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Subcommand: server
    server_parser = subparsers.add_parser("server", help="Start the VisiFlow local HTTP daemon server")
    server_parser.add_argument("--host", default="127.0.0.1", help="Host IP to bind (default: 127.0.0.1)")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")

    # Subcommand: ui
    ui_parser = subparsers.add_parser("ui", help="Launch the local interactive Web Playground UI in your browser")
    ui_parser.add_argument("--host", default="127.0.0.1", help="Host IP to bind (default: 127.0.0.1)")
    ui_parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")

    # Subcommand: match
    match_parser = subparsers.add_parser("match", help="Test visual target matching directly on an image file")
    match_parser.add_argument("image", help="Path to screenshot image file")
    match_parser.add_argument("query", help="Target text query string to find (e.g. 'Submit')")

    # Subcommand: mcp
    mcp_parser = subparsers.add_parser("mcp", help="Start the VisiFlow Model Context Protocol (MCP) Stdio server for AI agents (Cursor, Claude Desktop)")

    # Subcommand: run
    run_parser = subparsers.add_parser("run", help="Execute a declarative YAML or JSON visual E2E test file")
    run_parser.add_argument("test_file", help="Path to YAML/JSON test file (e.g. test.yaml)")
    run_parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    run_parser.add_argument("--headed", action="store_true", help="Run browser with visible UI")
    run_parser.add_argument("--report", default=None, help="Output path for self-healing HTML report")
    run_parser.add_argument("--browser", default="chromium", choices=["chromium", "firefox", "webkit"], help="Browser engine")

    # Clean raw args to prevent wrapper script path artifacts
    raw_args = sys.argv[1:]
    while raw_args and ("visiflow" in raw_args[0].lower() or raw_args[0].endswith(".exe")):
        raw_args = raw_args[1:]

    args = parser.parse_args(raw_args)

    if args.command == "server":
        try:
            import uvicorn
        except ImportError:
            print("Error: 'uvicorn' is required for the server. Run 'pip install uvicorn fastapi python-multipart'")
            sys.exit(1)
        print(f"Starting VisiFlow Daemon on http://{args.host}:{args.port}")
        uvicorn.run("visiflow.server:app", host=args.host, port=args.port, log_level="info")
    elif args.command == "ui":
        try:
            import uvicorn
        except ImportError:
            print("Error: 'uvicorn' is required for the UI. Run 'pip install uvicorn fastapi python-multipart'")
            sys.exit(1)
        url = f"http://{args.host}:{args.port}/ui"
        print(f"Opening VisiFlow Web Playground at {url}...")
        webbrowser.open(url)
        uvicorn.run("visiflow.server:app", host=args.host, port=args.port, log_level="info")
    elif args.command == "mcp":
        from .mcp import start_mcp_server
        start_mcp_server()
    elif args.command == "run":
        from .runner import VisiFlowYAMLRunner
        runner = VisiFlowYAMLRunner(args.test_file)
        headless = True if args.headless else (False if args.headed else None)
        success = runner.execute(headless=headless, report_path=args.report, browser_type=args.browser)
        sys.exit(0 if success else 1)
    elif args.command == "match":
        img_path = Path(args.image)
        if not img_path.exists():
            print(f"Error: Image file '{args.image}' does not exist.")
            sys.exit(1)
        detector = VisiFlowDetector()
        coords = detector.find_element_by_text(str(img_path), args.query)
        if coords:
            print(f"Match found for '{args.query}' at coordinates (X: {coords[0]}, Y: {coords[1]})")
        else:
            print(f"No match found for '{args.query}'")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
