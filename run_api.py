"""Start the FastAPI web server (uvicorn).

Usage:
    python run_api.py               # default port 8000
    python run_api.py --port 9000   # custom port
"""

import argparse
import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agentic RTL Debugger – Web UI server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable hot-reload for development")
    args = parser.parse_args()

    print(f"\n🚀  Agentic RTL Debugger UI")
    print(f"    http://{args.host}:{args.port}\n")

    uvicorn.run(
        "app.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
