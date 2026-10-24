"""The private data bundle: only staged tables go in (never the originals), and a deployment
uses it only when its SHA-256, its manifest and its paths all check out. Served from a local
stand-in host, like the assistant's tests."""

import io
import json
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from irerero.data import bundle

TOKEN = "read-only-test-token"  # pragma: allowlist secret


@pytest.fixture
def staged(tmp_path: Path) -> Path:
    raw = tmp_path / "raw"
    (raw / "census_2022").mkdir(parents=True)
    (raw / "census_2022" / "census_2022_sectors.csv").write_text("sector_name,children_3_5\nA,10\n")
    (raw / "projections").mkdir()
    (raw / "projections" / "nisr_projections_2023_2032.csv").write_text("district_name,year\n")
    (raw / "_received" / "census_2022_sample").mkdir(parents=True)
    (raw / "_received" / "census_2022_sample" / "records.csv").write_text("person-level\n")
    return raw


def test_the_bundle_holds_staged_tables_and_never_the_originals(staged, tmp_path):
    path, digest, files = bundle.make(staged, tmp_path / "out.zip")
    assert files == [
        "census_2022/census_2022_sectors.csv",
        "projections/nisr_projections_2023_2032.csv",
    ]
    names = zipfile.ZipFile(path).namelist()
    assert not [n for n in names if "_received" in n]
    assert bundle.sha256(path.read_bytes()) == digest
    # the same files give the same zip, so the checksum in the secrets stays valid
    assert bundle.make(staged, tmp_path / "again.zip")[1] == digest


def test_unpack_puts_the_files_in_place_and_records_the_bundle(staged, tmp_path):
    path, digest, _ = bundle.make(staged, tmp_path / "out.zip")
    target = tmp_path / "server_raw"
    bundle.unpack(path.read_bytes(), digest, target)
    assert (target / "census_2022" / "census_2022_sectors.csv").read_text().startswith("sector")
    assert bundle.current(target) == digest
    assert not (target / "_received").exists()


def _zip(files: dict[str, bytes], manifest: dict[str, str] | None = None) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
        listed = (
            manifest if manifest is not None else {n: bundle.sha256(d) for n, d in files.items()}
        )
        zf.writestr(bundle.MANIFEST, json.dumps({"files": listed}))
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("data", "words"),
    [
        (_zip({"census_2022/a.csv": b"x"}, {"census_2022/a.csv": "0" * 64}),
         "does not match the manifest"),
        (_zip({"../../app/views/national.py": b"x"}), "unexpected path"),
        (_zip({"/etc/passwd": b"x"}), "unexpected path"),
        (_zip({"not_a_dataset/a.csv": b"x"}), "unexpected path"),
        (_zip({"census_2022/a.csv": b"x"}, {}), "do not match its manifest"),
        (b"not a zip", "not a valid IrereroAI bundle"),
    ],
)  # fmt: skip
def test_a_bundle_that_does_not_check_out_writes_nothing(tmp_path, data, words):
    target = tmp_path / "server_raw"
    with pytest.raises(bundle.BundleError, match=words):
        bundle.unpack(data, bundle.sha256(data), target)
    assert not target.exists() or not any(target.iterdir())


def test_a_wrong_checksum_is_refused(staged, tmp_path):
    path, _, _ = bundle.make(staged, tmp_path / "out.zip")
    with pytest.raises(bundle.BundleError, match="SHA-256 does not match"):
        bundle.unpack(path.read_bytes(), "0" * 64, tmp_path / "server_raw")


@pytest.fixture
def host(staged, tmp_path):
    """A stand-in for the private host: serves the zip only with the right token."""
    path, digest, _ = bundle.make(staged, tmp_path / "out.zip")
    data, hits = path.read_bytes(), []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            hits.append(self.path)
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                self.send_response(401)
                self.end_headers()
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}/irerero-data.zip", digest, hits
    server.shutdown()


def test_sync_fetches_once_then_keeps_the_copy(host, tmp_path):
    url, digest, hits = host
    secrets = {"IRERERO_DATA_URL": url, "IRERERO_DATA_TOKEN": TOKEN, "IRERERO_DATA_SHA256": digest}
    target = tmp_path / "server_raw"
    assert bundle.sync(secrets, target) == "updated"
    assert bundle.sync(secrets, target) == "current" and len(hits) == 1
    assert (target / "projections" / "nisr_projections_2023_2032.csv").exists()


def test_sync_without_settings_is_off_and_errors_never_show_the_token(host, tmp_path):
    url, digest, _ = host
    assert bundle.sync({}, tmp_path / "raw") == "off"
    with pytest.raises(bundle.BundleError, match="SHA256 is not set"):
        bundle.sync({"IRERERO_DATA_URL": url}, tmp_path / "raw")
    wrong = {"IRERERO_DATA_URL": url, "IRERERO_DATA_TOKEN": "nope", "IRERERO_DATA_SHA256": digest}
    with pytest.raises(bundle.BundleError) as caught:
        bundle.sync(wrong, tmp_path / "raw")
    assert "401" in str(caught.value) and "nope" not in str(caught.value)
    assert url not in str(caught.value)
    with pytest.raises(bundle.BundleError, match="https"):
        bundle.sync({**wrong, "IRERERO_DATA_URL": "ftp://example.org/x.zip"}, tmp_path / "raw")
