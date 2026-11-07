import hashlib
from pathlib import Path

from grd.release import release_info


def test_public_release_reports_only_build_identity(env, monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "a" * 40)
    response = env.client.get("/health/release")
    assert response.status_code == 200
    result = response.json()
    assert result["version"] == "1.4.1"
    assert result["commit"] == "a" * 40
    assert result["source_url"].endswith("/tree/" + "a" * 40)
    assert set(result) == {"version", "tag", "repository", "evaluation_protocol", "android_version_code", "commit", "source_url", "release_url"}
    monkeypatch.setenv("RENDER_GIT_COMMIT", "not-a-commit-or-setting")
    assert release_info()["commit"] == "unreported"


def test_evidence_requires_authentication_and_exposes_reproducible_source(env):
    assert env.client.get("/api/v1/benchmarks/evaluation").status_code == 401
    result = env.client.get("/api/v1/benchmarks/evaluation", headers=env.headers)
    assert result.status_code == 200
    body = result.json()
    expected = hashlib.sha256((Path(__file__).resolve().parents[1] / "grd/assets/pharma-salesdaily.csv").read_bytes()).hexdigest()
    assert body["forecast"]["source_sha256"] == expected
    assert body["forecast"]["configuration"] == {"replicates": 10000, "block_origins": 8, "seed": 20261107, "test_origins": 52}
    assert body["inventory"]["configuration"]["seeds"] >= 200
    assert len(body["inventory"]["frontiers"]["selected"]) == 7
    assert body["inventory"]["measured_grd_impact"] is False
