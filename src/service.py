from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import secrets
import sqlite3
import string
from typing import Iterator
from urllib.parse import urlsplit


CODE_ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 8
MAX_CODE_ATTEMPTS = 5


@dataclass(frozen=True)
class ShortLink:
    short_code: str
    original_url: str
    created_at: datetime
    click_count: int

    def to_dict(self) -> dict[str, str | int | datetime]:
        return {
            "short_code": self.short_code,
            "original_url": self.original_url,
            "created_at": self.created_at,
            "click_count": self.click_count,
        }


class ShortLinkService:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS short_links (
                    short_code TEXT PRIMARY KEY,
                    original_url TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    click_count INTEGER NOT NULL DEFAULT 0 CHECK (click_count >= 0)
                )
                """
            )

    def create(self, original_url: str) -> ShortLink:
        normalized_url = self._validate_url(original_url)
        created_at = datetime.now(timezone.utc)

        for _ in range(MAX_CODE_ATTEMPTS):
            short_code = self._new_code()
            with self._connect() as connection:
                cursor = connection.execute(
                    """
                    INSERT INTO short_links (short_code, original_url, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(short_code) DO NOTHING
                    """,
                    (short_code, normalized_url, created_at.isoformat()),
                )
                if cursor.rowcount == 1:
                    return ShortLink(
                        short_code=short_code,
                        original_url=normalized_url,
                        created_at=created_at,
                        click_count=0,
                    )

        raise RuntimeError("Could not allocate a unique short code after several attempts.")

    def get(self, short_code: str) -> ShortLink:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM short_links WHERE short_code = ?",
                (short_code,),
            ).fetchone()
        if row is None:
            raise KeyError(short_code)
        return self._to_link(row)

    def resolve(self, short_code: str) -> str:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE short_links
                SET click_count = click_count + 1
                WHERE short_code = ?
                """,
                (short_code,),
            )
            if cursor.rowcount == 0:
                raise KeyError(short_code)
            row = connection.execute(
                "SELECT original_url FROM short_links WHERE short_code = ?",
                (short_code,),
            ).fetchone()
        return str(row["original_url"])

    def analytics(self, short_code: str) -> dict[str, str | int]:
        link = self.get(short_code)
        return {
            "short_code": link.short_code,
            "original_url": link.original_url,
            "created_at": link.created_at.isoformat(),
            "click_count": link.click_count,
        }

    @staticmethod
    def _validate_url(original_url: str) -> str:
        normalized_url = original_url.strip()
        parsed_url = urlsplit(normalized_url)
        if (
            parsed_url.scheme.lower() not in {"http", "https"}
            or not parsed_url.hostname
        ):
            raise ValueError("URL must be an absolute HTTP or HTTPS URL.")
        return normalized_url

    @staticmethod
    def _new_code() -> str:
        return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))

    @staticmethod
    def _to_link(row: sqlite3.Row) -> ShortLink:
        return ShortLink(
            short_code=str(row["short_code"]),
            original_url=str(row["original_url"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            click_count=int(row["click_count"]),
        )
