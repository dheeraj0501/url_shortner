# Shortlink

A runnable URL shortener demo built with FastAPI and SQLite. It creates short links, redirects visitors to their original destinations, and counts successful redirects. A small browser form is available at the root page, and the API is explorable through Swagger UI.

This is a demo application, not a production service.

## Candidate approach

I kept the scope centered on the core shortener flow:

1. Accept and validate an absolute HTTP or HTTPS URL.
2. Generate a compact, random code and persist it with the original URL.
3. Redirect a request for that code and increment its click count.
4. Expose link details and basic analytics so the flow can be demonstrated and tested.

The implementation separates HTTP handling (`agentic_system/api.py`), request/response schemas (`agentic_system/models.py`), and persistence and link behavior (`agentic_system/service.py`). SQLite and Python's standard library keep local setup small.

## Key decisions, assumptions, and tradeoffs

- **Random eight-character codes:** Codes are easy to share and avoid exposing sequential database IDs. Collisions are handled by a uniqueness constraint and retry. This is adequate for a small demo, not a globally coordinated allocation strategy.
- **SQLite persistence:** Links and click counts survive restarts without a separate database service. SQLite is appropriate for a single-instance demo; high write concurrency or multi-instance deployments would warrant a managed database.
- **Count redirects as clicks:** A click is counted when the redirect is successfully resolved. There is no event history, bot filtering, unique-visitor tracking, or analytics aggregation.
- **HTTP 302 redirects:** Redirects are temporary so browsers and intermediaries are less likely to cache them permanently.
- **Local demo, no authentication:** Anyone who can reach the app can create links and inspect counts. Authentication, quotas, abuse prevention, expiration, and custom aliases are outside scope.
- **No LLM or external API key:** URL creation, redirects, and analytics run locally; only Python dependencies are required.
- **Input validation:** The API accepts only absolute HTTP/HTTPS URLs. The redirect destination is the user-provided original URL; the application does not fetch it.

See [docs/architecture.md](docs/architecture.md) for the routes, data flow, and implementation details.

## Requirements

- Python 3.10+
- pip

## Setup and run (Windows PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run_api.py
```

Open:

- Demo form: <http://127.0.0.1:8000/>
- Swagger UI: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/health>

The SQLite database is created at `data/shortener.db` by default. Override its location with `SHORTENER_DB_PATH` before starting the server:

```powershell
$env:SHORTENER_DB_PATH = 'C:\path\to\shortener.db'
python run_api.py
```

## Try it with the demo client

Start the server in one terminal, then in another:

```powershell
.\.venv\Scripts\Activate.ps1
python demo.py https://example.com/some/long/path
```

The client prints the short URL. Open it in a browser to follow the redirect.

## API

### Create a short link

`POST /api/v1/links`

```json
{
  "url": "https://example.com/some/long/path"
}
```

Returns `201 Created` with the short code, short URL, original URL, creation time, and current click count.

### Follow a short link

`GET /r/{short_code}`

Returns a `302` redirect and increments the click count. Unknown codes return `404`.

### Read link details and analytics

- `GET /api/v1/links/{short_code}` returns link metadata and count.
- `GET /api/v1/analytics/{short_code}` returns the basic click analytics.

## Test

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = '1'
python -m pytest -q
```

Tests use temporary SQLite databases and do not modify the demo database.
