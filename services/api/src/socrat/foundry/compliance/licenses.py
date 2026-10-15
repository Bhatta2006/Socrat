import json
import math
import re
from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass(frozen=True)
class License:
    spdx: str = "unknown"
    confidence: float = 0
    evidence: str = "none"
    url: str = ""

    @property
    def category(self) -> str:
        key = self.spdx.lower()
        if not math.isfinite(self.confidence) or not 0.8 <= self.confidence <= 1:
            return "unknown"
        if "-nd" in key:
            return "noderivs"
        if "-nc" in key:
            return "noncommercial"
        if key in {
            "cc-by-sa-4.0",
            "cc-by-sa-3.0",
            "gpl-2.0-only",
            "gpl-3.0-only",
            "gpl-3.0-or-later",
        }:
            return "open_sharealike"
        if key in {
            "mit",
            "apache-2.0",
            "bsd-2-clause",
            "bsd-3-clause",
            "cc0-1.0",
            "cc-by-4.0",
            "cc-by-3.0",
        }:
            return "open_permissive"
        return "all_rights" if key != "unknown" else "unknown"

    @property
    def permits_storage(self) -> bool:
        return self.category in {"open_permissive", "open_sharealike"}


def identify(value: str, evidence: str, confidence: float) -> License:
    lower = value.strip().lower()
    cc = re.search(
        r"creativecommons\.org/(?:licenses/([a-z-]+)/|publicdomain/(zero)/)([0-9.]+)", lower
    )
    if cc:
        spdx = f"cc-{cc[1]}-{cc[3]}" if cc[1] else f"cc0-{cc[3]}"
    else:
        match = re.search(
            r"\b(?:CC-BY(?:-NC)?(?:-SA|-ND)?-[34]\.0|CC0-1\.0|MIT|Apache-2\.0|BSD-[23]-Clause|GPL-[23]\.0-(?:only|or-later))\b",
            value,
            re.I,
        )
        spdx = match[0] if match else "unknown"
    return License(
        spdx,
        confidence if spdx != "unknown" else 0,
        evidence,
        value if value.startswith("https://creativecommons.org/") else "",
    )


class Signals(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.licenses: list[License] = []
        self.optout = False
        self.restricted = False
        self.script_type = ""
        self.jsonld: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if len(a) != len(attrs):
            self.restricted = True
        if tag == "link" and "license" in (a.get("rel") or "").lower().split():
            self.licenses.append(identify(a.get("href") or "", "rel_license", 0.95))
        if tag == "meta":
            name, content = (a.get("name") or "").lower(), (a.get("content") or "").lower()
            if name in {"robots", "socratbot", "tdm-reservation"} and (
                re.search(r"\b(noai|notrain|noarchive)\b", content)
                or name == "tdm-reservation"
                and content != "0"
            ):
                self.optout = True
        if tag == "script":
            self.script_type = a.get("type") or ""
        if tag in {"input", "form"} and (
            a.get("type") == "password" or "login" in (a.get("action") or "").lower()
        ):
            self.restricted = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.script_type = ""

    def handle_data(self, data):
        if self.script_type == "application/ld+json":
            self.jsonld.append(data)


def page_signals(body: bytes, api: License | None = None) -> tuple[License, bool, bool]:
    text = body.decode("utf-8", "replace")
    signals = Signals()
    signals.feed(text)
    if re.search(
        r"captcha|cf-chl-|sign in to continue|subscribe to continue|paywall", text[:64000], re.I
    ):
        signals.restricted = True
    candidates = [api] if api is not None else []
    candidates += signals.licenses
    if re.search(r"\ball rights reserved\b", text, re.I):
        candidates.append(License("LicenseRef-All-Rights-Reserved", 0.95, "rights_notice"))
    for raw in signals.jsonld:
        try:
            value = json.loads(raw)
            nodes = [value]
            while nodes:
                node = nodes.pop()
                if isinstance(node, list):
                    nodes.extend(node)
                if isinstance(node, dict):
                    if (
                        node.get("isAccessibleForFree") is False
                        or node.get("isAccessibleForFree") == "false"
                    ):
                        signals.restricted = True
                    if isinstance(node.get("license"), str):
                        candidates.append(identify(node["license"], "jsonld", 0.9))
                    nodes.extend(v for v in node.values() if isinstance(v, (dict, list)))
        except ValueError:
            continue
    # Footer prose alone cannot meet the storage-confidence threshold.
    footer = identify(text[-4000:], "footer_unverified", 0.5)
    if footer.spdx != "unknown" and any(
        c.confidence >= 0.8 and c.spdx.lower() != footer.spdx.lower() for c in candidates
    ):
        return License(evidence="conflicting_license_text"), signals.optout, signals.restricted
    candidates.append(footer)
    if any(c.category in {"noderivs", "noncommercial", "all_rights"} for c in candidates):
        return (
            next(
                c for c in candidates if c.category in {"noderivs", "noncommercial", "all_rights"}
            ),
            signals.optout,
            signals.restricted,
        )
    known = [c for c in candidates if c.confidence >= 0.8]
    if len({c.spdx.lower() for c in known}) > 1:
        return License(evidence="conflicting_licenses"), signals.optout, signals.restricted
    return (known[0] if known else License()), signals.optout, signals.restricted


def license_file(body: bytes) -> License:
    text = body.decode("utf-8", "replace")
    if (
        "Permission is hereby granted, free of charge" in text
        and "THE SOFTWARE IS PROVIDED" in text
    ):
        return License("MIT", 0.95, "license_file")
    if "Apache License" in text and "Version 2.0" in text:
        return License("Apache-2.0", 0.95, "license_file")
    if "GNU GENERAL PUBLIC LICENSE" in text and "Version 3" in text:
        return License("GPL-3.0-only", 0.9, "license_file")
    return License(evidence="license_file_unrecognized")
