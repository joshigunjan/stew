#!/usr/bin/env python3
"""
Clara (Helmholtz Edition): Open-source, sovereign AI Data Steward.
Launcher entrypoint.
"""
import argparse
import sys
import uvicorn

from clara.config import config

def main():
    parser = argparse.ArgumentParser(description="Clara: Sovereign AI Data Steward (Helmholtz Edition)")
    parser.add_argument("--host", default=config.host, help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=config.port, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable live auto-reload for development")
    args = parser.parse_args()

    print("=" * 65)
    print("🛰️  CLARA: Sovereign AI Data Steward (Helmholtz Edition)")
    print("=" * 65)
    print(f"📡 Web Portal:     http://{args.host}:{args.port}")
    print(f"🔗 Blablador Host: {config.blablador_base_url}")
    print(f"🤖 Default Model:  {config.default_model}")
    print(f"🔒 Data Sovereign: All processing local / Helmholtz Cloud (JSC)")
    print("=" * 65)

    uvicorn.run(
        "clara.api.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )

if __name__ == "__main__":
    main()
