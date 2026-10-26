"""Custom interface/API integration: real HTTP requests against a loopback server."""

import hashlib
import io
import json
import zipfile
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from mc_options.reporting.artifacts import ROOT
from mc_options.web import BUSY, execute, make_server


@pytest.fixture(scope="module")
def local_server():
    server = make_server(0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def request(base, route, config=None, headers=None):
    data = json.dumps(config).encode() if config is not None else None
    return urlopen(Request(base + route, data=data, headers=headers or {}), timeout=30)


def test_static_and_research_do_not_sample(local_server):
    before = set((ROOT / "reports/experiments").iterdir())
    with request(local_server, "/api/health") as response:
        assert json.load(response) == {"status": "ok", "interface": "custom", "local_only": True}
    for route, expected in [("/", b"The pricing lab"), ("/static/app.js", b"api/run")]:
        with request(local_server, route) as response:
            assert expected in response.read()
    with request(local_server, "/api/research") as response:
        data = json.load(response)
        assert data["available"]
        assert data["estimate_count"] == 21600
        assert data["case_count"] == 24
        assert len(data["rows"]) == 9
    assert before == set((ROOT / "reports/experiments").iterdir())


def test_price_save_restore_and_downloads(local_server):
    config = {"product": "European", "samples": 1000, "seed": 42, "method": "control"}
    with request(local_server, "/api/run", config) as response:
        data = json.load(response)
    assert set(data["estimates"]) == {"ordinary", "antithetic", "control"}
    assert data["estimates"]["antithetic"]["effective_samples"] == 500
    assert data["estimates"]["control"]["pilot_samples"] == 100
    identifier = data["run_id"]
    with request(local_server, f"/api/runs/{identifier}/result") as response:
        assert json.load(response) == data
    with request(local_server, f"/api/runs/{identifier}/config") as response:
        assert json.load(response) == data["config"]
        assert "attachment" in response.headers["Content-Disposition"]
    with request(local_server, f"/api/runs/{identifier}/csv") as response:
        text = response.read().decode()
        assert "ordinary" in text and "control" in text
    with request(local_server, f"/api/runs/{identifier}/zip") as response:
        with zipfile.ZipFile(io.BytesIO(response.read())) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            assert manifest["status"] == "succeeded"
            for artifact in manifest["artifacts"]:
                name = artifact["file_uri"].split("/")[-1]
                assert hashlib.sha256(archive.read(name)).hexdigest() == artifact["sha256"]
            assert "visual_paths.npz" in archive.namelist()
            assert "web_result.json" in archive.namelist()


@pytest.mark.parametrize(
    "config",
    [
        {"option": {"volatility": -1}},
        {"samples": 2_000_001},
        {"seed": True},
        {"product": "American"},
        {"product": "Arithmetic Asian", "observation_dates": [0.5, 0.5]},
        {"product": "Arithmetic Asian", "observation_dates": [0.5, 1], "method": "antithetic"},
    ],
)
def test_invalid_request_keeps_saved_runs(local_server, config):
    before = set((ROOT / "reports/experiments").iterdir())
    with pytest.raises(HTTPError) as error:
        request(local_server, "/api/run", config)
    assert error.value.code == 400
    assert json.load(error.value)["error"]
    assert before == set((ROOT / "reports/experiments").iterdir())


def test_local_boundary_and_concurrency(local_server):
    with pytest.raises(HTTPError) as error:
        request(local_server, "/api/run", {"samples": 1000}, {"Origin": "https://example.com"})
    assert error.value.code == 403
    BUSY.acquire()
    try:
        with pytest.raises(HTTPError) as error:
            request(local_server, "/api/run", {"samples": 1000})
        assert error.value.code == 429
    finally:
        BUSY.release()
    with pytest.raises(HTTPError) as error:
        request(local_server, "/api/runs/not-a-uuid/result")
    assert error.value.code == 404


def test_asian_custom_flow_and_seed():
    config = {
        "product": "Arithmetic Asian",
        "observation_dates": [0.25, 0.5, 0.75, 1],
        "samples": 1000,
        "seed": 99,
        "method": "control",
    }
    first = execute(config)
    second = execute(config)
    assert set(first["estimates"]) == {"ordinary", "control"}
    assert first["estimates"]["control"]["benchmark_price"] is None
    assert first["estimates"]["control"]["absolute_error"] is None
    assert first["estimates"]["control"]["price"] == second["estimates"]["control"]["price"]
    assert first["control_reference"] > 0
