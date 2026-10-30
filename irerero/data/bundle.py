"""A private data bundle for a deployment: the staged tables, never the originals.

    python -m irerero.data.bundle            (make bundle) -> data/bundle/irerero-data.zip

The bundle holds what `make intake` staged in data/raw/<dataset>/ (aggregates: sector counts,
district projections, boundaries, district rates) and a MANIFEST.json with the SHA-256 of
each file. It never holds data/raw/_received/, so the census sample records and every other
original stay on the machine that received them.

A deployment fetches it on first start when three secrets are set (Streamlit secrets or
environment variables):

    IRERERO_DATA_URL      where the zip is, e.g. a file in a private GitHub repository
    IRERERO_DATA_TOKEN    a read-only token for that place (optional for other hosts)
    IRERERO_DATA_SHA256   the zip's SHA-256, printed by `make bundle`

The zip is used only if its SHA-256 matches, every file matches the manifest, and every path
is a known dataset folder. Anything else leaves data/raw/ untouched and the app on the demo
bundle, with a notice saying why.

A single file kept beside the zip in the same private repository can be fetched the same way,
with the same token: the school list, when IRERERO_SCHOOLS_PATH names it (its path in the
repository, e.g. schools/Rwandapreprimarydata_locatios.GeoJSON). IRERERO_SCHOOLS_SHA256 is
optional; when set, the file must match it. The file must be a GeoJSON FeatureCollection, and
lands in data/raw/schools/schools.geojson.
"""

import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections.abc import Mapping
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

from irerero.config import DATA, RAW
from irerero.data.registry import FILE_DATASETS

BUNDLE = DATA / "bundle" / "irerero-data.zip"
MANIFEST = "MANIFEST.json"
MARKER = ".bundle_sha256"  # in data/raw/: which bundle the files there came from
DATASETS = frozenset(d.key for d in FILE_DATASETS)
SCHOOLS_DIR, SCHOOLS_FILE = "schools", "schools.geojson"  # where data/sources/schools reads
SCHOOLS_MARKER = ".source_sha256"  # in data/raw/schools/: which download the file came from
SETTINGS = (
    "IRERERO_DATA_URL",
    "IRERERO_DATA_TOKEN",
    "IRERERO_DATA_SHA256",
    "IRERERO_SCHOOLS_PATH",
    "IRERERO_SCHOOLS_URL",
    "IRERERO_SCHOOLS_SHA256",
)
MAX_BYTES = 200 * 1024 * 1024
TIMEOUT = 60


class BundleError(Exception):
    """Why a bundle was not used, in words that hold no secret."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- making -------------------------------------------------------------------------------
def make(raw: Path = RAW, out: Path = BUNDLE) -> tuple[Path, str, list[str]]:
    """(zip, its SHA-256, files) from the staged dataset folders in `raw`."""
    files = sorted(
        p
        for key in sorted(DATASETS)
        if (raw / key).is_dir()
        for p in (raw / key).rglob("*")
        if p.is_file() and not p.name.startswith(".")
    )
    if not files:
        raise BundleError(f"nothing staged in {raw}: run `make intake` first")
    manifest = {
        "files": {p.relative_to(raw).as_posix(): sha256(p.read_bytes()) for p in files},
        "note": "Staged aggregates only; originals stay in data/raw/_received/.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:  # fixed timestamps, so the same files give the same zip
            info = zipfile.ZipInfo(path.relative_to(raw).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo(MANIFEST, (2026, 1, 1, 0, 0, 0))
        zf.writestr(info, json.dumps(manifest, indent=1, sort_keys=True))
    data = buffer.getvalue()
    out.write_bytes(data)
    return out, sha256(data), list(manifest["files"])


# --- using --------------------------------------------------------------------------------
def settings(secrets: Mapping[str, Any] | None = None) -> dict[str, str | None]:
    """Secrets win over environment variables, as for the assistant."""

    def get(key: str) -> str | None:
        value = (secrets or {}).get(key) or os.environ.get(key)
        return str(value).strip().strip("\"'").strip() if value else None  # pasted quotes

    return {k: get(k) for k in SETTINGS}


def _download(url: str, token: str | None) -> bytes:
    if not url.startswith("https://") and not url.startswith("http://127.0.0.1"):
        raise BundleError("IRERERO_DATA_URL must be an https address")
    headers = {"User-Agent": "IrereroAI"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if url.startswith("https://api.github.com/"):
        headers["Accept"] = "application/vnd.github.raw"
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 (https only, above)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310
            data = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        hint = " (check IRERERO_DATA_TOKEN)" if error.code in (401, 403, 404) else ""
        raise BundleError(f"the data host answered {error.code}{hint}") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise BundleError("could not reach the data host") from None
    if len(data) > MAX_BYTES:
        raise BundleError("the download is larger than expected")
    return data


def describe(data: bytes) -> str:
    """What a download looks like, to tell a wrong file from a wrong address. Holds no secret:
    only the size and the kind of content."""
    head = data[:200].lstrip().lower()
    if data[:4] == b"PK\x03\x04":
        kind = "a zip file"
    elif head.startswith((b"<!doctype html", b"<html")):
        kind = "a web page, not the file: use the api.github.com/repos/.../contents/... address"
    elif head.startswith(b"{"):
        kind = "JSON (not a zip: the host may not have returned the raw file)"
    else:
        kind = "an unknown file"
    return f"{kind}, {len(data):,} bytes"


def unpack(data: bytes, expected_sha256: str, raw: Path = RAW) -> list[str]:
    """Check the zip and put its files in `raw`. Nothing is written unless every check passes."""
    found = sha256(data)
    expected = expected_sha256.strip().strip("\"'").strip().lower()
    if found != expected:
        raise BundleError(
            f"the bundle's SHA-256 does not match IRERERO_DATA_SHA256 (received {describe(data)};"
            f" its SHA-256 starts {found[:12]}, the secret's starts {expected[:12]})"
        )
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        manifest = json.loads(zf.read(MANIFEST))["files"]
    except (zipfile.BadZipFile, KeyError, ValueError):
        raise BundleError("the bundle is not a valid IrereroAI bundle") from None
    names = [n for n in zf.namelist() if n != MANIFEST and not n.endswith("/")]
    if sorted(names) != sorted(manifest):
        raise BundleError("the bundle's files do not match its manifest")
    for name in names:
        parts = PurePosixPath(name).parts
        if name.startswith("/") or ".." in parts or len(parts) < 2 or parts[0] not in DATASETS:
            raise BundleError(f"unexpected path in the bundle: {name}")
        if sha256(zf.read(name)) != manifest[name]:
            raise BundleError(f"{name} does not match the manifest")
    # all checks passed: replace the dataset folders the bundle carries, atomically per folder
    raw.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=raw) as tmp:
        for name in names:
            target = Path(tmp) / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(name))
        for key in sorted({PurePosixPath(n).parts[0] for n in names}):
            shutil.rmtree(raw / key, ignore_errors=True)
            (Path(tmp) / key).rename(raw / key)
    (raw / MARKER).write_text(found)
    return names


def current(raw: Path = RAW) -> str | None:
    marker = raw / MARKER
    return marker.read_text().strip() if marker.exists() else None


def sync(secrets: Mapping[str, Any] | None = None, raw: Path = RAW) -> str:
    """Fetch the configured bundle if it is not already in `raw`. Returns "off" (not set up),
    "current" (already there) or "updated" (fetched: rebuild). Raises BundleError."""
    s = settings(secrets)
    if not s["IRERERO_DATA_URL"]:
        return "off"
    if not s["IRERERO_DATA_SHA256"]:
        raise BundleError("IRERERO_DATA_SHA256 is not set, so the bundle cannot be checked")
    if current(raw) == s["IRERERO_DATA_SHA256"].lower():
        return "current"
    unpack(_download(s["IRERERO_DATA_URL"], s["IRERERO_DATA_TOKEN"]), s["IRERERO_DATA_SHA256"], raw)
    return "updated"


def schools_url(s: Mapping[str, str | None]) -> str | None:
    """Where the school list is: IRERERO_SCHOOLS_URL, or IRERERO_SCHOOLS_PATH inside the same
    GitHub repository as the bundle (taken from IRERERO_DATA_URL). None when not set up."""
    if s.get("IRERERO_SCHOOLS_URL"):
        return s["IRERERO_SCHOOLS_URL"]
    path = s.get("IRERERO_SCHOOLS_PATH")
    if not path:
        return None
    base = s.get("IRERERO_DATA_URL") or ""
    repo = re.match(r"^(https://api\.github\.com/repos/[^/]+/[^/]+)/contents/", base)
    if not repo:
        raise BundleError(
            "IRERERO_SCHOOLS_PATH needs IRERERO_DATA_URL to be an "
            "api.github.com/repos/<owner>/<repo>/contents/... address (or set IRERERO_SCHOOLS_URL)"
        )
    return f"{repo.group(1)}/contents/{quote(path.strip().strip('/'))}"


def schools_current(raw: Path = RAW) -> str | None:
    marker = raw / SCHOOLS_DIR / SCHOOLS_MARKER
    return marker.read_text().strip() if marker.exists() else None


def sync_schools(secrets: Mapping[str, Any] | None = None, raw: Path = RAW) -> str:
    """Fetch the configured school list into data/raw/schools/. Returns "off", "current" (the
    same file is already there) or "updated" (rebuild). Raises BundleError; nothing is written
    unless the file checks out."""
    s = settings(secrets)
    url = schools_url(s)
    if not url:
        return "off"
    data = _download(url, s["IRERERO_DATA_TOKEN"])
    found = sha256(data)
    expected = (s["IRERERO_SCHOOLS_SHA256"] or "").lower()
    if expected and found != expected:
        raise BundleError(
            f"the school list's SHA-256 does not match IRERERO_SCHOOLS_SHA256 (received "
            f"{describe(data)}; its SHA-256 starts {found[:12]}, the secret's {expected[:12]})"
        )
    try:
        parsed = json.loads(data.decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        raise BundleError(f"the school list is not GeoJSON (received {describe(data)})") from None
    if not isinstance(parsed, dict) or parsed.get("type") != "FeatureCollection":
        raise BundleError("the school list is not a GeoJSON FeatureCollection")
    if schools_current(raw) == found and (raw / SCHOOLS_DIR / SCHOOLS_FILE).exists():
        return "current"
    folder = raw / SCHOOLS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    partial = folder / f"{SCHOOLS_FILE}.part"
    partial.write_bytes(data)
    partial.replace(folder / SCHOOLS_FILE)  # whole file or nothing
    (folder / SCHOOLS_MARKER).write_text(found)
    return "updated"


def fingerprint(raw: Path = RAW) -> str:
    """Which fetched data the tables were built from: the bundle, and the school list."""
    schools = schools_current(raw)
    return (current(raw) or "") + (f"+schools:{schools[:16]}" if schools else "")


def main() -> int:
    try:
        path, digest, files = make()
    except BundleError as error:
        print(error)
        return 1
    root = DATA.parent
    print(
        f"Wrote {path.relative_to(root)} ({path.stat().st_size / 1e6:.1f} MB, {len(files)} files):"
    )
    for name in files:
        print(f"  {name}")
    print(f"\nIRERERO_DATA_SHA256 = {digest}")
    print("Keep the zip private. See docs/deploy_private_data.md for the next steps.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
