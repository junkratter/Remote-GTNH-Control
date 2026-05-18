"""Entry-point for the GTNH Cyber backend.

Usage:
    python run.py --host 0.0.0.0 --port 1030
"""

from __future__ import annotations

import argparse

import uvicorn

from app.core.settings import settings
from app.core.logging import LOG_LEVEL


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GTNH Cyber backend")
    parser.add_argument("--host", "-H", default=settings.host, help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", "-P", type=int, default=settings.port, help="Bind port (default: 1030)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload (dev only)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    log_config = uvicorn.config.LOGGING_CONFIG
    fmt = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    log_config["formatters"]["access"]["fmt"] = fmt
    log_config["formatters"]["default"]["fmt"] = fmt

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=log_config,
        log_level=LOG_LEVEL,
    )


if __name__ == "__main__":
    main()
