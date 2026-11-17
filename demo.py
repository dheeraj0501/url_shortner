from __future__ import annotations

import argparse
import json
from urllib.error import URLError
from urllib.request import Request, urlopen


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a short link using the running demo.")
    parser.add_argument("url", help="HTTP or HTTPS URL to shorten")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="Base URL of the running API")
    args = parser.parse_args()

    request = Request(
        f"{args.api.rstrip('/')}/api/v1/links",
        data=json.dumps({"url": args.url}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=10) as response:
            result = json.load(response)
    except URLError as exc:
        raise SystemExit(f"Could not reach the API at {args.api}: {exc}") from exc

    print(f"Short URL: {result['short_url']}")
    print(f"Code:      {result['short_code']}")


if __name__ == "__main__":
    main()
