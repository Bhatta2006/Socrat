from socrat.foundry.acquisition.http import Fetcher
from socrat.foundry.compliance import PolicyBlocked
from socrat.foundry.jobs import STAGES, StageResult, stub
from socrat.foundry.storage import LocalStore, S3Store


def acquisition_handlers(engine, *, wire=None, store=None, limiter=None):
    def client(context):
        storage = store or (
            S3Store(context.settings.s3_bucket, context.settings.s3_endpoint_url)
            if context.settings.s3_bucket
            else LocalStore(context.settings.snapshot_directory)
        )
        return Fetcher(engine, wire=wire, store=storage, limiter=limiter)

    def compliance(context):
        fetcher = client(context)
        urls = context.input.get("payload", {}).get("urls", [])
        if (
            not isinstance(urls, list)
            or len(urls) > context.settings.max_docs_per_job
            or any(not isinstance(u, str) for u in urls)
        ):
            raise PolicyBlocked("invalid_source_list")
        ids, blocked = [], 0
        for url in urls:
            try:
                ids.append(fetcher.candidate(url, context))
            except PolicyBlocked:
                blocked += 1
        return StageResult({"candidates": ids, "blocked": blocked})

    def acquire(context):
        fetcher = client(context)
        records = []
        for url in context.input.get("payload", {}).get("urls", []):
            try:
                fetched = fetcher.fetch(url, context)
                records.append({"source": fetched.source_id, "policy": fetched.policy})
            except PolicyBlocked:
                records.append({"policy": "blocked"})
        return StageResult({"sources": records})

    return {**dict.fromkeys(STAGES, stub), "S2": compliance, "S3": acquire}
