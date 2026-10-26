import base64
import hashlib
import io
import json
import zipfile

import pytest

from mc_options.browser import browser_run
from mc_options.config import Option
from mc_options.models.estimators import simulate


@pytest.mark.parametrize("maturity", [0, 1])
def test_browser_reuses_estimators_and_exports_verified_artifacts(maturity):
    config = {"option": {"maturity": maturity}, "samples": 1000, "seed": 42}
    result = json.loads(browser_run(json.dumps(config)))
    for method, estimate in result["estimates"].items():
        expected = simulate(Option(maturity=maturity), 1000, 42, method).estimate
        assert estimate["price"] == expected.price
        assert estimate["standard_error"] == expected.standard_error
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(result["archive_base64"]))) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        for artifact in manifest["artifacts"]:
            assert hashlib.sha256(archive.read(artifact["name"])).hexdigest() == artifact["sha256"]


def test_browser_caps_compute_budget():
    with pytest.raises(ValueError, match="200,000"):
        browser_run(json.dumps({"samples": 200001}))
