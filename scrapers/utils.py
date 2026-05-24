"""Shared utilities for all scrapers — retry, logging, data validation."""
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, TypeVar

import requests

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

T = TypeVar("T")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36 IndiaEnergyDashboard/1.0"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def retry(fn: Callable[[], T], attempts: int = 3, delay: float = 5.0) -> T:
    """Retry a callable up to *attempts* times with exponential back-off."""
    last_exc: Exception = RuntimeError("No attempts made")
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            wait = delay * (2**i)
            logging.warning(f"Attempt {i+1}/{attempts} failed: {exc}. Retrying in {wait:.0f}s…")
            time.sleep(wait)
    raise last_exc


def safe_get(url: str, timeout: int = 30, **kwargs) -> requests.Response:
    """GET with retry, shared headers, and timeout."""
    def _get():
        r = requests.get(url, headers=HEADERS, timeout=timeout, **kwargs)
        r.raise_for_status()
        return r
    return retry(_get)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def update_metadata(source: str, status: str = "ok") -> None:
    """Stamp last-updated time for a given source into data/metadata.json."""
    meta_path = DATA_DIR / "metadata.json"
    meta: dict = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
    meta[source] = {"updated_at": utc_now_iso(), "status": status}
    write_json(meta_path, meta)
