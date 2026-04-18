"""CLI entry: `python -m dota2_coach` starts MCP server + GSI HTTP.

Add `--selftest` to run a dry import/registration check without opening stdio.
"""
from __future__ import annotations

import argparse
import asyncio
import io
import sys


def _force_utf8_streams() -> None:
    # Windows 默认代码页 (cp936/cp932) 会让 Chinese 日志在 stdout/stderr 上抛 UnicodeEncodeError.
    for attr in ("stdout", "stderr"):
        stream = getattr(sys, attr, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, io.UnsupportedOperation):
            pass


def main() -> None:
    _force_utf8_streams()
    parser = argparse.ArgumentParser(prog="dota2-coach")
    parser.add_argument("--selftest", action="store_true", help="Verify imports and tool registration, then exit")
    args = parser.parse_args()

    from .server import run, run_selftest

    if args.selftest:
        rc = asyncio.run(run_selftest())
        sys.exit(rc)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
