"""Health-gated staging deploy and rollback controller."""

import argparse
import json
import os
import re
import subprocess
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
IMAGE_PATTERN = re.compile(r"^ghcr\.io/[a-z0-9._-]+/[a-z0-9._/-]+@sha256:[0-9a-f]{64}$")
HOST_PATTERN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


class Release:
    __slots__ = (
        "commit",
        "api_image",
        "web_image",
        "staging_host",
        "tls_email",
        "oidc_issuer",
        "oidc_client_id",
        "secrets_dir",
    )

    def __init__(
        self,
        *,
        commit: str,
        api_image: str,
        web_image: str,
        staging_host: str,
        tls_email: str,
        oidc_issuer: str,
        oidc_client_id: str,
        secrets_dir: str,
    ):
        if not COMMIT_PATTERN.fullmatch(commit):
            raise ValueError("commit must be a full lowercase Git SHA")
        if not IMAGE_PATTERN.fullmatch(api_image) or not IMAGE_PATTERN.fullmatch(web_image):
            raise ValueError(
                "application images must be lowercase GHCR references pinned by digest"
            )
        if not HOST_PATTERN.fullmatch(staging_host):
            raise ValueError("staging_host must be an owned lowercase DNS name")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", tls_email):
            raise ValueError("tls_email must be a valid operational email address")
        issuer = urlparse(oidc_issuer)
        if issuer.scheme != "https" or not issuer.netloc or issuer.query or issuer.fragment:
            raise ValueError("oidc_issuer must be an HTTPS issuer URL")
        if not oidc_client_id or any(character.isspace() for character in oidc_client_id):
            raise ValueError("oidc_client_id must be non-empty and contain no whitespace")
        if not secrets_dir.startswith("/"):
            raise ValueError("secrets_dir must be an absolute path on the staging host")

        self.commit = commit
        self.api_image = api_image
        self.web_image = web_image
        self.staging_host = staging_host
        self.tls_email = tls_email
        self.oidc_issuer = oidc_issuer
        self.oidc_client_id = oidc_client_id
        self.secrets_dir = secrets_dir

    def __eq__(self, other):
        return isinstance(other, Release) and self.as_dict() == other.as_dict()

    def as_dict(self):
        return {name: getattr(self, name) for name in self.__slots__}

    def environment(self):
        return {
            "SOCRAT_API_IMAGE": self.api_image,
            "SOCRAT_WEB_IMAGE": self.web_image,
            "STAGING_HOST": self.staging_host,
            "TLS_EMAIL": self.tls_email,
            "SOCRAT_OIDC_ISSUER": self.oidc_issuer,
            "SOCRAT_OIDC_CLIENT_ID": self.oidc_client_id,
            "SOCRAT_SECRETS_DIR": self.secrets_dir,
        }


class ReleaseStore:
    def __init__(self, root):
        self.root = Path(root)
        self.releases = self.root / "releases"

    def _atomic_write(self, path: Path, content: str):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(content, encoding="utf-8", newline="\n")
        temporary.chmod(0o600)
        os.replace(temporary, path)

    def _manifest_path(self, commit: str):
        return self.releases / f"{commit}.json"

    def env_path(self, commit: str):
        return self.releases / f"{commit}.env"

    def stage(self, release: Release):
        manifest = json.dumps(release.as_dict(), indent=2, sort_keys=True) + "\n"
        environment = "".join(
            f"{name}={json.dumps(value)}\n" for name, value in release.environment().items()
        )
        self._atomic_write(self._manifest_path(release.commit), manifest)
        self._atomic_write(self.env_path(release.commit), environment)
        return self.env_path(release.commit)

    def load(self, commit: str):
        if not COMMIT_PATTERN.fullmatch(commit):
            raise ValueError("release ID must be a full lowercase Git SHA")
        values = json.loads(self._manifest_path(commit).read_text(encoding="utf-8"))
        return Release(**values)

    def _pointer(self, name: str):
        path = self.root / name
        if not path.exists():
            return None
        value = path.read_text(encoding="utf-8").strip()
        if not COMMIT_PATTERN.fullmatch(value):
            raise ValueError(f"{name} release pointer is invalid")
        return value

    def current_id(self):
        return self._pointer("current")

    def previous_id(self):
        return self._pointer("previous")

    def promote(self, commit: str):
        self.load(commit)
        current = self.current_id()
        if current == commit:
            return
        if current:
            self._atomic_write(self.root / "previous", f"{current}\n")
        elif (self.root / "previous").exists():
            (self.root / "previous").unlink()
        self._atomic_write(self.root / "current", f"{commit}\n")


class ReleaseController:
    def __init__(self, store: ReleaseStore, runner):
        self.store = store
        self.runner = runner

    def deploy(self, release: Release):
        env_file = self.store.stage(release)
        prior_id = self.store.current_id()
        try:
            self.runner.activate(release, env_file)
        except Exception:
            if prior_id:
                prior = self.store.load(prior_id)
                self.runner.activate(prior, self.store.env_path(prior_id))
            raise
        self.store.promote(release.commit)

    def rollback(self):
        previous_id = self.store.previous_id()
        if not previous_id:
            raise ValueError("no previous release is available")
        previous = self.store.load(previous_id)
        self.runner.activate(previous, self.store.env_path(previous_id))
        self.store.promote(previous_id)
        return previous


class DockerComposeRunner:
    def __init__(self, compose_file: Path, health_attempts=12, health_interval=5):
        self.compose_file = compose_file.resolve()
        self.health_attempts = health_attempts
        self.health_interval = health_interval

    def _compose(self, env_file: Path, *arguments):
        subprocess.run(
            [
                "docker",
                "compose",
                "--project-name",
                "socrat-staging",
                "--env-file",
                str(env_file),
                "--file",
                str(self.compose_file),
                *arguments,
            ],
            cwd=self.compose_file.parent,
            check=True,
        )

    def _verify_health(self, release: Release):
        endpoint = f"https://{release.staging_host}/api/health/ready"
        last_error = None
        for attempt in range(self.health_attempts):
            try:
                with urllib.request.urlopen(endpoint, timeout=10) as response:
                    payload = json.load(response)
                    if response.status == 200 and payload == {"status": "ready"}:
                        return
            except Exception as exc:
                last_error = exc
            if attempt + 1 < self.health_attempts:
                time.sleep(self.health_interval)
        raise RuntimeError("staging health check failed") from last_error

    def activate(self, release: Release, env_file: Path):
        self._compose(env_file, "config", "--quiet")
        self._compose(env_file, "pull")
        self._compose(
            env_file,
            "up",
            "--detach",
            "--remove-orphans",
            "--wait",
            "--wait-timeout",
            "240",
        )
        self._verify_health(release)


def parser():
    root = Path(__file__).resolve().parents[2]
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--state-dir", default="/var/lib/socrat/releases")
    cli.add_argument(
        "--compose-file", default=str(root / "infra" / "runtime" / "staging" / "compose.yaml")
    )
    commands = cli.add_subparsers(dest="command", required=True)

    deploy = commands.add_parser("deploy")
    deploy.add_argument("--commit", required=True)
    deploy.add_argument("--api-image", required=True)
    deploy.add_argument("--web-image", required=True)
    deploy.add_argument("--staging-host", required=True)
    deploy.add_argument("--tls-email", required=True)
    deploy.add_argument("--oidc-issuer", required=True)
    deploy.add_argument("--oidc-client-id", required=True)
    deploy.add_argument("--secrets-dir", default="/opt/socrat/secrets")
    commands.add_parser("rollback")
    return cli


def main():
    args = parser().parse_args()
    store = ReleaseStore(args.state_dir)
    controller = ReleaseController(store, DockerComposeRunner(Path(args.compose_file)))
    if args.command == "deploy":
        release = Release(
            commit=args.commit,
            api_image=args.api_image,
            web_image=args.web_image,
            staging_host=args.staging_host,
            tls_email=args.tls_email,
            oidc_issuer=args.oidc_issuer,
            oidc_client_id=args.oidc_client_id,
            secrets_dir=args.secrets_dir,
        )
        controller.deploy(release)
        print(json.dumps({"event": "release_promoted", "commit": release.commit}))
    else:
        release = controller.rollback()
        print(json.dumps({"event": "release_rolled_back", "commit": release.commit}))


if __name__ == "__main__":
    main()
