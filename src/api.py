from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from src.models import AnalyticsResponse, CreateLinkRequest, LinkResponse
from src.service import ShortLinkService


DEMO_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Shortlink demo</title>
    <style>
      body { font: 16px system-ui, sans-serif; margin: 3rem auto; max-width: 42rem; padding: 0 1rem; }
      h1 { margin-bottom: .5rem; }
      form { display: flex; gap: .5rem; margin: 2rem 0; }
      input { flex: 1; min-width: 0; padding: .7rem; }
      button { padding: .7rem 1rem; cursor: pointer; }
      #result, #error { overflow-wrap: anywhere; }
      #error { color: #a11; }
    </style>
  </head>
  <body>
    <h1>Shortlink</h1>
    <p>Paste a URL to create a short link. Open the link to test its redirect.</p>
    <form id="shorten-form">
      <input id="url" type="url" placeholder="https://example.com/page" required>
      <button type="submit">Shorten</button>
    </form>
    <p id="result" aria-live="polite"></p>
    <p id="error" role="alert"></p>
    <p><a href="/docs">Explore the API in Swagger UI</a></p>
    <script>
      const form = document.getElementById("shorten-form");
      const result = document.getElementById("result");
      const error = document.getElementById("error");
      form.addEventListener("submit", async (event) => {
        event.preventDefault();
        result.replaceChildren();
        error.textContent = "";
        try {
          const response = await fetch("/api/v1/links", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: document.getElementById("url").value })
          });
          const data = await response.json();
          if (!response.ok) {
            throw new Error(data.detail || "Could not create the short link.");
          }
          const link = document.createElement("a");
          link.href = data.short_url;
          link.textContent = data.short_url;
          link.target = "_blank";
          link.rel = "noopener noreferrer";
          result.append("Short link: ", link);
        } catch (reason) {
          error.textContent = reason.message;
        }
      });
    </script>
  </body>
</html>
"""


def create_app(service: ShortLinkService | None = None) -> FastAPI:
    short_link_service = service or ShortLinkService(
        os.getenv("SHORTENER_DB_PATH", "data/shortener.db")
    )
    app = FastAPI(
        title="Shortlink",
        description="A small URL shortener demo with redirects and click counts.",
        version="1.0.0",
    )

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def home() -> str:
        return DEMO_PAGE

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post(
        "/api/v1/links",
        response_model=LinkResponse,
        status_code=status.HTTP_201_CREATED,
        summary="Create a short link",
    )
    def create_link(payload: CreateLinkRequest, request: Request) -> dict[str, Any]:
        link = short_link_service.create(str(payload.url))
        return {
            **link.to_dict(),
            "short_url": f"{str(request.base_url).rstrip('/')}/r/{link.short_code}",
        }

    @app.get(
        "/api/v1/links/{short_code}",
        response_model=LinkResponse,
        summary="Get link details",
    )
    def get_link(short_code: str, request: Request) -> dict[str, Any]:
        try:
            link = short_link_service.get(short_code)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Short link not found") from exc
        return {
            **link.to_dict(),
            "short_url": f"{str(request.base_url).rstrip('/')}/r/{link.short_code}",
        }

    @app.get(
        "/api/v1/analytics/{short_code}",
        response_model=AnalyticsResponse,
        summary="Get click analytics",
    )
    def get_analytics(short_code: str) -> dict[str, Any]:
        try:
            return short_link_service.analytics(short_code)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Short link not found") from exc

    @app.get(
        "/r/{short_code}",
        summary="Redirect to the original URL",
        responses={302: {"description": "Redirect to original URL"}},
    )
    def redirect_short_link(short_code: str) -> RedirectResponse:
        try:
            original_url = short_link_service.resolve(short_code)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="Short link not found") from exc
        return RedirectResponse(url=original_url, status_code=status.HTTP_302_FOUND)

    return app


app = create_app()
