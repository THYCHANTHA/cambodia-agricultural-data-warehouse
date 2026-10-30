"""HTTP helpers with retry/backoff and streamed, checksummed downloads."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import requests

log = logging.getLogger(__name__)
USER_AGENT = "cambodia-agricultural-data-warehouse/0.1 (academic research prototype)"


def get_with_retry(
    url: str, *, params: dict | None = None, timeout: int = 120, retries: int = 4
) -> requests.Response:
    """GET with exponential backoff on network errors and 5xx/429 responses."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": USER_AGENT})
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"{resp.status_code} from {url}")
            resp.raise_for_status()
            return resp
        except (requests.RequestException, requests.HTTPError) as exc:
            last = exc
            wait = 2**attempt
            log.warning("GET %s failed (%s); retry %d/%d in %ss", url, exc, attempt + 1, retries, wait)
            time.sleep(wait)
    raise RuntimeError(f"GET {url} failed after {retries} attempts") from last


def download_file(url: str, dest: Path, *, timeout: int = 300, retries: int = 3) -> dict:
    """Stream `url` to `dest` and return provenance metadata (size, sha256)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for attempt in range(retries):
        try:
            sha = hashlib.sha256()
            size = 0
            with requests.get(url, stream=True, timeout=timeout, headers={"User-Agent": USER_AGENT}) as r:
                r.raise_for_status()
                with open(dest, "wb") as fh:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        fh.write(chunk)
                        sha.update(chunk)
                        size += len(chunk)
            return {"url": url, "path": str(dest), "bytes": size, "sha256": sha.hexdigest()}
        except requests.RequestException as exc:
            last = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"download of {url} failed after {retries} attempts") from last
