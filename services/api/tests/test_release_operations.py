"""Release-state and rollback behavior without requiring a Docker daemon."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "scripts" / "operations" / "release.py"


def load_release_module():
    spec = importlib.util.spec_from_file_location("socrat_release", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def release_module():
    return load_release_module()


def make_release(module, digit: str):
    commit = digit * 40
    digest = digit * 64
    return module.Release(
        commit=commit,
        api_image=f"ghcr.io/bhatta2006/socrat-api@sha256:{digest}",
        web_image=f"ghcr.io/bhatta2006/socrat-web@sha256:{digest}",
        staging_host="learn.example.com",
        tls_email="operations@example.com",
        oidc_issuer="https://identity.example.com/application/o/socrat/",
        oidc_client_id="socrat-staging",
        secrets_dir="/opt/socrat/secrets",
    )


def test_release_rejects_mutable_or_mismatched_images(release_module):
    with pytest.raises(ValueError, match="digest"):
        release_module.Release(
            commit="a" * 40,
            api_image="ghcr.io/bhatta2006/socrat-api:latest",
            web_image="ghcr.io/bhatta2006/socrat-web@sha256:" + "a" * 64,
            staging_host="learn.example.com",
            tls_email="operations@example.com",
            oidc_issuer="https://identity.example.com",
            oidc_client_id="socrat-staging",
            secrets_dir="/opt/socrat/secrets",
        )


def test_release_store_writes_only_non_secret_configuration(tmp_path, release_module):
    store = release_module.ReleaseStore(tmp_path)
    release = make_release(release_module, "a")
    env_file = store.stage(release)

    content = env_file.read_text(encoding="utf-8")
    assert "SOCRAT_API_IMAGE=" in content
    assert "SOCRAT_WEB_IMAGE=" in content
    assert "STAGING_HOST=" in content
    assert "PASSWORD" not in content.upper()
    assert "SECRET=" not in content.upper()
    assert store.load(release.commit) == release


class FakeRunner:
    def __init__(self, failing_commit=None):
        self.failing_commit = failing_commit
        self.activations = []

    def activate(self, release, env_file):
        self.activations.append((release.commit, env_file))
        if release.commit == self.failing_commit:
            raise RuntimeError("health check failed")


def test_deploy_promotes_only_after_healthy_activation(tmp_path, release_module):
    store = release_module.ReleaseStore(tmp_path)
    runner = FakeRunner()
    controller = release_module.ReleaseController(store, runner)
    release = make_release(release_module, "a")

    controller.deploy(release)

    assert store.current_id() == release.commit
    assert store.previous_id() is None
    assert [commit for commit, _ in runner.activations] == [release.commit]


def test_failed_deploy_restores_previous_release_without_promotion(tmp_path, release_module):
    store = release_module.ReleaseStore(tmp_path)
    old_release = make_release(release_module, "a")
    store.stage(old_release)
    store.promote(old_release.commit)
    failed_release = make_release(release_module, "b")
    runner = FakeRunner(failing_commit=failed_release.commit)
    controller = release_module.ReleaseController(store, runner)

    with pytest.raises(RuntimeError, match="health check failed"):
        controller.deploy(failed_release)

    assert store.current_id() == old_release.commit
    assert store.previous_id() is None
    assert [commit for commit, _ in runner.activations] == [
        failed_release.commit,
        old_release.commit,
    ]


def test_explicit_rollback_swaps_current_and_previous(tmp_path, release_module):
    store = release_module.ReleaseStore(tmp_path)
    runner = FakeRunner()
    controller = release_module.ReleaseController(store, runner)
    old_release = make_release(release_module, "a")
    new_release = make_release(release_module, "b")
    controller.deploy(old_release)
    controller.deploy(new_release)

    rolled_back = controller.rollback()

    assert rolled_back.commit == old_release.commit
    assert store.current_id() == old_release.commit
    assert store.previous_id() == new_release.commit
    assert runner.activations[-1][0] == old_release.commit
