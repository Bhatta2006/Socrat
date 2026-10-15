import ipaddress
import queue
import re
import socket
import threading
from urllib.parse import parse_qsl

import httpx

from socrat.foundry.compliance import PolicyBlocked


def public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return (
        value != "168.63.129.16"
        and ip.is_global
        and not ip.is_multicast
        and not ip.is_unspecified
        and not ip.is_reserved
        and not getattr(ip, "is_site_local", False)
        and not getattr(ip, "ipv4_mapped", None)
        and not (
            isinstance(ip, ipaddress.IPv6Address)
            and (
                ip.sixtofour
                or ip.teredo
                or ip in ipaddress.ip_network("64:ff9b::/96")
                or ip in ipaddress.ip_network("64:ff9b:1::/48")
            )
        )
    )


def canonical_url(value: str) -> httpx.URL:
    if len(value) > 2048 or any(ord(c) < 33 for c in value) or "\\" in value:
        raise PolicyBlocked("invalid_url")
    try:
        url = httpx.URL(value)
        host = url.host.rstrip(".").lower()
        if (
            url.scheme not in {"http", "https"}
            or not host
            or url.username
            or url.password
            or url.port not in {80, 443, None}
            or "%" in host
        ):
            raise ValueError()
        try:
            if not public_ip(host):
                raise PolicyBlocked("private_address")
        except ValueError:
            if (
                not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?", host)
                or "." not in host
                or host.endswith((".localhost", ".local", ".internal"))
            ):
                raise PolicyBlocked("invalid_host") from None
        if any(
            re.search(r"token|password|secret|credential|signature|api.?key", k, re.I)
            for k, _ in parse_qsl(url.query.decode())
        ):
            raise PolicyBlocked("credentials_in_url")
        return url.copy_with(host=host, fragment=None)
    except (ValueError, httpx.InvalidURL):
        raise PolicyBlocked("invalid_url") from None


def resolve_public(host: str, port: int, timeout: float) -> str:
    """Bound DNS waiting without ever connecting from the resolver thread."""
    result: queue.Queue = queue.Queue(maxsize=1)

    def resolve():
        try:
            result.put(socket.getaddrinfo(host, port, type=socket.SOCK_STREAM))
        except OSError:
            result.put(None)

    threading.Thread(target=resolve, daemon=True).start()
    try:
        addresses = result.get(timeout=timeout)
    except queue.Empty:
        raise PolicyBlocked("dns_timeout") from None
    if not addresses:
        raise PolicyBlocked("dns_unavailable")
    ips = {item[4][0] for item in addresses}
    if not all(public_ip(ip) for ip in ips):
        raise PolicyBlocked("private_address")
    return sorted(ips)[0]
