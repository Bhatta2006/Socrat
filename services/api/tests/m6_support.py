from m4_support import diagnostic_pack
from m5_support import completed

from socrat.execution.protocol import Limits, RuntimeProfile
from socrat.skillpacks.schema import SkillPack

SIGNING = "synthetic-signing-" + "a" * 64
WORKER = "synthetic-worker-" + "b" * 64


def profiles():
    return [
        RuntimeProfile(
            id=f"{language}_1",
            language=language,
            image=f"ghcr.io/socrat/{language}@sha256:{digit * 64}",
            limits=Limits(memory_mb=512 if language == "java" else 256),
            attestation_reference="synthetic-tests-only",
        ).model_dump()
        for language, digit in (("python", "1"), ("cpp", "2"), ("java", "3"))
    ]


def code_pack():
    payload = diagnostic_pack().model_dump()
    root = SkillPack.model_validate(payload).topological_order()[0]
    commands = dict(
        python="print(int(input()) * 2)\n",
        cpp="#include <iostream>\nint main(){int n;std::cin>>n;std::cout<<n*2;}\n",
        java="public class Solution{public static void main(String[] a){java.util.Scanner s=new java.util.Scanner(System.in);System.out.println(s.nextInt()*2);}}\n",
    )
    variants = [
        dict(
            language=x["language"],
            starter_code=commands[x["language"]],
            reference_solution=commands[x["language"]],
            interface="Read integer stdin and print twice its value",
            runtime_ref=x["image"],
            time_limit_ms=2000,
            memory_limit_mb=x["limits"]["memory_mb"],
        )
        for x in profiles()
    ]
    payload["exercises"].append(
        dict(
            id="a_runtime_probe",
            title="Synthetic double",
            concept_ids=[root],
            inventory="practice",
            modality="code",
            evidence_mode="implement",
            statement="Read a whole number and print twice its value.",
            rubric="Semantic integer result",
            difficulty=1,
            calibration="reviewed",
            estimated_minutes=5,
            family_id="runtime_probe",
            variants=variants,
            tests=[
                dict(input="2\n", expected="4\n", visibility="public"),
                dict(input="718\n", expected="1436\n", visibility="hidden"),
            ],
            provenance=payload["provenance"],
            accessibility="Keyboard editor and screen reader",
        )
    )
    return SkillPack.model_validate(payload)


def setup(platform, monkeypatch, track="foundations", language="python"):
    # completed() patches M4 authoring via planner_pack; replace that callable first.
    monkeypatch.setattr("m5_support.planner_pack", code_pack)
    app, client, headers, goal = completed(platform, monkeypatch, track, language)
    settings = app.state.settings
    settings.execution_enabled = True
    from pydantic import SecretStr

    settings.execution_signing_secret = SecretStr(SIGNING)
    settings.execution_worker_secret = SecretStr(WORKER)
    settings.execution_profiles = profiles()
    worker_headers = {"Origin": headers["Origin"], "Authorization": "Bearer " + WORKER}
    assert (
        client.post(
            "/api/v1/execution/worker/heartbeat",
            headers=worker_headers,
            json=dict(worker_id="worker-1", images=[x["image"] for x in profiles()]),
        ).status_code
        == 200
    )
    from datetime import datetime
    from zoneinfo import ZoneInfo

    weekday = datetime.now(ZoneInfo(goal["goal"]["timezone"])).weekday()
    weekdays = sorted({weekday, (weekday + 2) % 7, (weekday + 4) % 7})
    path = f"/api/v1/goals/{goal['id']}/curriculum/commands"
    draft = client.post(
        path,
        headers=headers,
        json=dict(
            action="generate", expected_revision=0, idempotency_key="m6-plan", weekdays=weekdays
        ),
    ).json()
    assert "review_digest" in draft, draft
    assert (
        client.post(
            path,
            headers=headers,
            json=dict(
                action="confirm",
                expected_revision=draft["revision"],
                idempotency_key="m6-confirm",
                reviewed_digest=draft["review_digest"],
            ),
        ).status_code
        == 200
    )
    return app, client, headers, worker_headers, goal
