"""Start the sandbox: ``python -m sandbox --port 0 --build release --log sandbox.log``.

Prints one line, ``SANDBOX READY http://host:port``, when it accepts requests
(with ``--port 0`` the operating system chooses a free port).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence

from aiohttp import web

from sandbox.app import System, create_app
from sandbox.config import BUILDS, Config, Timings


async def serve(config: Config, host: str, port: int) -> None:
    system = System(config)
    runner = web.AppRunner(create_app(system), access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    system.start()
    actual_port = runner.addresses[0][1]
    print(f"SANDBOX READY http://{host}:{actual_port}", flush=True)
    logging.getLogger("sandbox").info("started: build=%s port=%s", config.build, actual_port)
    await asyncio.Event().wait()  # until the process is terminated


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m sandbox", description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--build", choices=sorted(BUILDS), default="release")
    parser.add_argument("--log", help="log file (default: standard error)")
    parser.add_argument(
        "--gateway-latency", type=float, default=Timings.gateway_latency, help="payment gateway latency (s)"
    )
    parser.add_argument(
        "--concurrency",
        action="append",
        default=[],
        metavar="SUBSCRIPTION=N",
        help="worker tasks for a subscription, e.g. payments=4 (default 1 each)",
    )
    args = parser.parse_args(argv)
    concurrency = {}
    for item in args.concurrency:
        name, _, count = item.partition("=")
        concurrency[name] = int(count)
    config = Config.for_build(args.build, Timings(gateway_latency=args.gateway_latency), concurrency)
    handler: logging.Handler = (
        logging.FileHandler(args.log, encoding="utf-8") if args.log else logging.StreamHandler()
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-5s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    try:
        asyncio.run(serve(config, args.host, args.port))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
