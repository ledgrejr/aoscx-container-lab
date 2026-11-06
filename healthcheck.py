import argparse
import json
import time
from pathlib import Path


APP_NAME = "aoscx-container-healthcheck"
APP_VERSION = Path(__file__).with_name("VERSION").read_text(encoding="ascii").strip()


def health_report():
    return {
        "application": APP_NAME,
        "checks": {"process": "ok"},
        "status": "healthy",
        "version": APP_VERSION,
    }


def main(arguments=None):
    parser = argparse.ArgumentParser(description="Emit a local container health status.")
    parser.add_argument("--check", action="store_true", help="emit one status and exit")
    parser.add_argument("--interval", type=float, default=30.0, help="heartbeat interval in seconds")
    options = parser.parse_args(arguments)
    if options.interval <= 0:
        parser.error("--interval must be greater than zero")

    while True:
        print(json.dumps(health_report(), sort_keys=True, separators=(",", ":")), flush=True)
        if options.check:
            return 0
        time.sleep(options.interval)


if __name__ == "__main__":
    raise SystemExit(main())