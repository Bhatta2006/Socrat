"""Real native Windows/POSIX execution, never simulated result callbacks."""

import time

import psutil
import pytest
from runner.local_backend import LocalProcessBackend
from runner.worker import execute

from socrat.execution.protocol import (
    COMMANDS,
    JobEnvelope,
    JobManifest,
    RuntimeProfile,
    TestInput,
    canonical,
    hashed,
    sign,
)
from socrat.models import identifier

SECRET = "native-test-signing-secret-" * 3


def envelope(source, language="python", **limits):
    profile = RuntimeProfile.model_validate(
        dict(
            id="local_" + language,
            language=language,
            image="socrat/local-" + language + "@sha256:" + "a" * 64,
            attestation_reference="Insecure local development toolchain",
            limits=dict(
                wall_seconds=2,
                compile_seconds=20,
                memory_mb=256,
                pids=8,
                output_bytes=4096,
                **limits,
            ),
        )
    )
    tests = [
        TestInput(input="2\n", expected="4", visibility="public"),
        TestInput(input="3\n", expected="6", visibility="hidden"),
    ]
    stamp = int(time.time())
    manifest = JobManifest(
        job_id=identifier(),
        attempt_id=identifier(),
        nonce="b" * 64,
        issued_at=stamp,
        expires_at=stamp + 600,
        language=language,
        image=profile.image,
        runtime_id=profile.id,
        code_hash=hashed(source.encode()),
        test_digest=hashed(canonical([x.model_dump() for x in tests])),
        pack_digest="sha256:" + "c" * 64,
        mode="submit",
        limits=profile.limits,
        compile_config=COMMANDS[language],
    )
    job = JobEnvelope(
        manifest=manifest, signature=sign(manifest.model_dump(), SECRET), source=source, tests=tests
    )
    return LocalProcessBackend([profile], environment="test", demo_mode=True), job


@pytest.mark.parametrize(
    "source,status",
    [
        ("print(int(input())*2)", "passed"),
        ("print(0)", "wrong_answer"),
        ("a=1\ndef broken(:\n  pass", "compile_error"),
        ("a=1\nraise ValueError('real traceback')", "runtime_error"),
        ("while True: pass", "timeout"),
        ("while True: print('X'*4096)", "output_limit"),
        ("x=bytearray(2_000_000_000)", "memory_limit"),
    ],
)
def test_native_python_results_and_cleanup(source, status, tmp_path):
    backend, job = envelope(source)
    backend.temp_root = tmp_path
    result = execute(job, backend, SECRET, int(time.time()))["result"]
    assert result["operational_status"] == "healthy"
    assert [x["status"] for x in result["cases"]] == [status, status]
    assert result["cases"][1]["stdout"] == result["cases"][1]["stderr"] == ""
    assert not list(tmp_path.iterdir())
    if status == "compile_error":
        assert "line 2" in result["cases"][0]["stderr"]
    if status == "runtime_error":
        assert "line 2" in result["cases"][0]["stderr"]
    assert len(result["cases"][0]["stdout"]) <= 4096


def test_no_secrets_and_no_oracle_files(monkeypatch):
    monkeypatch.setenv("SOCRAT_EXECUTION_SIGNING_SECRET", "private-never-leak")
    monkeypatch.setenv("PRIVATE_PROVIDER_KEY", "private-never-leak")
    source = "import os,pathlib\nassert not any('SOCRAT' in k or 'PRIVATE' in k for k in os.environ)\nassert sorted(x.name for x in pathlib.Path('.').iterdir()) == ['solution.py']\nprint(int(input())*2)"
    backend, job = envelope(source)
    assert all(x.status == "passed" for x in backend.execute(job))


def test_timeout_kills_descendants_and_spawn_is_contained(tmp_path):
    marker = "socrat-orphan-" + identifier()
    source = f"import subprocess,sys\nfor n in range(1000):\n subprocess.Popen([sys.executable,'-I','-B','-c','import time;time.sleep(60)',{marker!r}])\nwhile True: pass"
    backend, job = envelope(source)
    backend.temp_root = tmp_path
    assert all(
        x.status in {"timeout", "runtime_error", "memory_limit"} for x in backend.execute(job)
    )
    time.sleep(0.1)
    for process in psutil.process_iter(["cmdline"]):
        assert marker not in " ".join(process.info["cmdline"] or [])
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "environment,demo",
    [("production", True), ("staging", True), ("development", False), ("test", False)],
)
def test_local_process_guard(environment, demo):
    with pytest.raises(ValueError, match="demo mode"):
        LocalProcessBackend([], environment=environment, demo_mode=demo)


LANGUAGE_PROGRAMS = {
    "cpp": {
        "passed": "#include <iostream>\nint main(){int n;std::cin>>n;std::cout<<n*2;}",
        "wrong_answer": "#include <iostream>\nint main(){std::cout<<0;}",
        "compile_error": "#include <iostream>\nint main(){invalid_symbol;}",
        "runtime_error": "#include <cstdlib>\nint main(){std::abort();}",
        "timeout": "int main(){while(true){}}",
        "output_limit": '#include <iostream>\nint main(){while(true)std::cout<<"XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX";}',
        "memory_limit": "#include <vector>\nint main(){std::vector<char> x(2000000000); volatile char* p=x.data(); for(long i=0;i<2000000000;i++)p[i]=1;}",
    },
    "java": {
        "passed": "public class Solution {public static void main(String[] a){System.out.println(new java.util.Scanner(System.in).nextInt()*2);}}",
        "wrong_answer": "public class Solution {public static void main(String[] a){System.out.println(0);}}",
        "compile_error": "public class Solution {\npublic static void main(String[] a){invalid_symbol;}\n}",
        "runtime_error": 'public class Solution {\npublic static void main(String[] a){throw new RuntimeException("real traceback");}\n}',
        "timeout": "public class Solution {public static void main(String[] a){while(true){}}}",
        "output_limit": 'public class Solution {public static void main(String[] a){while(true)System.out.print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX");}}',
        "memory_limit": "public class Solution {public static void main(String[] a){byte[] x=new byte[2000000000];System.out.print(x.length);}}",
    },
}


@pytest.mark.parametrize("language", ["cpp", "java"])
@pytest.mark.parametrize("status", list(LANGUAGE_PROGRAMS["cpp"]))
def test_native_compiled_languages(language, status, tmp_path):
    backend, job = envelope(LANGUAGE_PROGRAMS[language][status], language)
    backend.temp_root = tmp_path
    result = execute(job, backend, SECRET, int(time.time()))["result"]
    assert result["operational_status"] == "healthy", "Required CI toolchain is missing"
    assert [case["status"] for case in result["cases"]] == [status, status]
    assert result["cases"][1]["stdout"] == result["cases"][1]["stderr"] == ""
    if status == "compile_error":
        assert ":2:" in result["cases"][0]["stderr"]
    assert not list(tmp_path.iterdir())
