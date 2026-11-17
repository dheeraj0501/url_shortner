# Shortlink architecture

## Overview

Shortlink is a single-process demo application. FastAPI serves a minimal browser form, JSON API, Swagger documentation, and redirect route. A service layer owns URL validation, code generation, link lookup, and click counting. SQLite stores each short code, destination URL, creation timestamp, and redirect count.

```text
Browser / API client
        |
        v
FastAPI routes and Pydantic validation
        |
        v
ShortLinkService
        |
        v
SQLite (data/shortener.db)
```

## Main flow

1. `POST /api/v1/links` validates the request as an HTTP or HTTPS URL.
2. The service generates an eight-character random code and inserts it into SQLite. A primary-key constraint prevents duplicates; a collision is retried.
3. The response includes a URL such as `http://127.0.0.1:8000/r/Ab3dE5fG`.
4. `GET /r/{short_code}` increments the stored count and returns a `302` redirect to the original URL.
5. Link metadata and the accumulated count are available from the link and analytics endpoints.

## Data model

`short_links` contains:

| Field | Purpose |
|---|---|
| `short_code` | Random public identifier and primary key |
| `original_url` | Validated HTTP/HTTPS destination |
| `created_at` | UTC timestamp of creation |
| `click_count` | Number of redirects resolved by this application |

The redirect count is updated atomically in SQLite. Separate short-lived connections are used per operation so requests do not share a mutable connection across worker threads.

## API routes

| Method | Route | Behavior |
|---|---|---|
| `POST` | `/api/v1/links` | Create a short link |
| `GET` | `/r/{short_code}` | Count and redirect |
| `GET` | `/api/v1/links/{short_code}` | Read link details |
| `GET` | `/api/v1/analytics/{short_code}` | Read click count |
| `GET` | `/health` | Basic liveness response |

## Tradeoffs and next steps

- SQLite avoids external infrastructure and preserves demo data across restarts. A multi-instance or high-throughput deployment should move persistence to a shared database.
- Counts are simple totals, not an analytics event stream. A production analytics design would store timestamped events and filter bots or repeated requests.
- Codes are randomly generated and collision checked. If the service grows, code allocation, expiration, and custom aliases need explicit product rules.
- The app has no authentication or rate limiting and should not be exposed as a public service without abuse controls.
- The application trusts the inbound host when constructing the returned short URL, which is suitable for local development. A deployed service should use a configured canonical public base URL and trusted-proxy settings.
