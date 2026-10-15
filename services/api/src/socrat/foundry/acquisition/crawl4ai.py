import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import replace

from socrat.foundry.acquisition.http import Fetched
from socrat.foundry.compliance import PolicyBlocked

CONVERT = """
import json, os, socket, sys
os.environ['PYTHON_DOTENV_DISABLED'] = '1'
def deny_network(*args, **kwargs):
    raise RuntimeError('network_disabled')
socket.socket.connect = deny_network
socket.socket.connect_ex = deny_network
socket.create_connection = deny_network
socket.getaddrinfo = deny_network
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
data = json.load(sys.stdin)
result = DefaultMarkdownGenerator(options={'ignore_images': True}).generate_markdown(
    data['html'], base_url=data['url'], citations=True)
print(json.dumps({'markdown': result.raw_markdown}))
"""


class Crawl4AIFetcher:
    """Use Crawl4AI's local converter after the shared HTTP/policy boundary; no browser."""

    def __init__(self, fetcher):
        self.fetcher = fetcher

    def fetch(self, url: str, context) -> Fetched:
        source = self.fetcher.fetch(url, context)
        markdown = ""
        if source.policy == "store":
            if importlib.util.find_spec("crawl4ai") is None:
                raise PolicyBlocked("markdown_extra_unavailable")
            context.reserve()
            # Crawl4AI imports dotenv and ML modules. Neither private env nor credentials enter it.
            env = {
                k: v
                for k, v in os.environ.items()
                if k in {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP"}
            }
            env["PYTHON_DOTENV_DISABLED"] = "1"
            with tempfile.TemporaryDirectory() as cwd:
                env["USERPROFILE"] = cwd
                env["CRAWL4_AI_BASE_DIRECTORY"] = cwd
                env["LITELLM_LOCAL_MODEL_COST_MAP"] = "1"
                try:
                    result = subprocess.run(
                        [sys.executable, "-I", "-c", CONVERT],
                        input=json.dumps(
                            {"html": source.body.decode("utf-8", "replace"), "url": source.url}
                        ),
                        text=True,
                        encoding="utf-8",
                        capture_output=True,
                        cwd=cwd,
                        env=env,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                        timeout=min(30, context.remaining_seconds()),
                        check=True,
                    )
                    markdown = json.loads(result.stdout)["markdown"]
                except (subprocess.SubprocessError, ValueError, KeyError):
                    raise PolicyBlocked("markdown_conversion_failed") from None
            if not isinstance(markdown, str) or len(markdown.encode()) > context.settings.max_bytes:
                raise PolicyBlocked("markdown_too_large")
        return replace(source, markdown=markdown)
