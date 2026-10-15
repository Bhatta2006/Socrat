import ssl
import time
from dataclasses import dataclass
from typing import Protocol

import httpcore

from socrat.foundry.compliance import PolicyBlocked
from socrat.foundry.compliance.urls import canonical_url, resolve_public


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes


class Wire(Protocol):
    live: bool

    def get(
        self, url: str, headers: dict[str, str], timeout: float, max_bytes: int
    ) -> Response: ...


class DeadlineStream(httpcore.NetworkStream):
    def __init__(self, stream, deadline):
        self.stream, self.deadline = stream, deadline

    def remaining(self, timeout):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise PolicyBlocked("request_timeout")
        return min(timeout, remaining) if timeout is not None else remaining

    def read(self, max_bytes, timeout=None):
        return self.stream.read(max_bytes, self.remaining(timeout))

    def write(self, buffer, timeout=None):
        return self.stream.write(buffer, self.remaining(timeout))

    def close(self):
        self.stream.close()

    def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        return DeadlineStream(
            self.stream.start_tls(ssl_context, server_hostname, self.remaining(timeout)),
            self.deadline,
        )

    def get_extra_info(self, info):
        return self.stream.get_extra_info(info)


class PublicBackend(httpcore.SyncBackend):
    def __init__(self, deadline):
        self.deadline = deadline

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise PolicyBlocked("request_timeout")
        ip = resolve_public(host, port, remaining)
        # Only a validated numeric IP reaches the socket. HTTP host and TLS SNI stay original.
        stream = super().connect_tcp(
            ip, port, min(timeout or remaining, remaining), local_address, socket_options
        )
        return DeadlineStream(stream, self.deadline)


class PublicWire:
    live = True

    def get(self, url: str, headers: dict[str, str], timeout: float, max_bytes: int) -> Response:
        canonical_url(url)
        deadline = time.monotonic() + timeout
        try:
            # A fresh pool forces destination validation on every request, including redirects.
            with httpcore.ConnectionPool(
                ssl_context=ssl.create_default_context(),
                retries=0,
                max_connections=1,
                network_backend=PublicBackend(deadline),
            ) as pool:
                with pool.stream(
                    "GET",
                    url,
                    headers=list(headers.items()),
                    extensions={
                        "timeout": dict.fromkeys(("connect", "read", "write", "pool"), timeout)
                    },
                ) as response:
                    selected: dict[str, str] = {}
                    for key, value in response.headers:
                        name, decoded = key.decode().lower(), value.decode("latin-1")
                        selected[name] = (
                            selected[name] + "," + decoded if name in selected else decoded
                        )
                    if selected.get("content-encoding", "identity").lower() != "identity":
                        raise PolicyBlocked("encoded_response")
                    body = bytearray()
                    # Restricted headers are enough to deny retention without reading content.
                    if not optout_headers(selected):
                        for chunk in response.iter_stream():
                            if time.monotonic() >= deadline:
                                raise PolicyBlocked("request_timeout")
                            body.extend(chunk)
                            if len(body) > max_bytes:
                                raise PolicyBlocked("response_too_large")
                    return Response(response.status, selected, bytes(body))
        except (httpcore.NetworkError, httpcore.TimeoutException, httpcore.ProtocolError):
            raise PolicyBlocked("network_unavailable") from None


def optout_headers(headers: dict[str, str]) -> bool:
    import re

    return (
        bool(re.search(r"\b(noai|notrain|noarchive)\b", headers.get("x-robots-tag", ""), re.I))
        or headers.get("tdm-reservation", "0").strip() != "0"
    )
