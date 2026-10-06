"""Check repository-authored references with containers or an explicit host compiler.

This does not exercise the execution worker, signed scoring, gVisor, or release
approval. The input is the fixed committed draft; no arbitrary input path is accepted.
The optional host mode executes only trusted repository references, never learner code.
"""

import argparse
import json
import os
import subprocess
import tempfile
from pathlib import Path

from socrat.learning.pilot import PilotDraft

ROOT = Path(__file__).resolve().parents[2]
DRAFT = ROOT / "contracts/content/m7-arrays-pilot-draft.json"
IMAGES = {
    "python": "python:3.12-slim-bookworm",
    "cpp": "gcc@sha256:5e927c284bf55a7dc796262e311a0703344f62f41f5621eb56843111b1d37e15",
    "java": "eclipse-temurin@sha256:3e3c176ffed168beb42c607be9bc1639b466cf00261a0fb04425562c9d0c5c2b",
}
PYTHON_HARNESS = """import contextlib, io, json, pathlib, sys
root=pathlib.Path('/draft')
for directory in sorted(root.iterdir()):
    if not directory.is_dir(): continue
    source=(directory/'reference.py').read_text()
    cases=json.loads((directory/'cases.json').read_text())
    for index,case in enumerate(cases):
        sys.stdin=io.TextIOWrapper(io.BytesIO(case['input'].encode()))
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(source, str(directory/'reference.py'), 'exec'), {})
        if output.getvalue().split()!=case['expected'].split():
            raise AssertionError(f'{directory.name}: case {index}')
    print(f'{directory.name}: {len(cases)} passed')
print(sys.version)
"""
CPP_HARNESS = """#define main reference_main
#include "reference.cpp"
#undef main
#include <fstream>
#include <sstream>
int main(int argc,char**argv){
 if(argc!=2)return 2;
 ifstream inputs(string(argv[1])+"/inputs.txt"), expected(string(argv[1])+"/expected.txt");
 string line,want; int count=0;
 while(getline(inputs,line)){
  if(!getline(expected,want))return 3;
  istringstream in(line),answers(want); int n;long long p,x;in>>n>>p;
  vector<long long>a(n),e;for(auto&v:a)in>>v;while(answers>>x)e.push_back(x);
  if(solve(a,p)!=e){cerr<<argv[1]<<": case "<<count<<" failed\\n";return 1;} count++;
 }
 cout<<argv[1]<<": "<<count<<" passed\\n";return 0;
}
"""
JAVA_HARNESS = """import java.nio.file.*;
import java.util.*;
public class Harness {
 public static void main(String[]args)throws Exception {
  var input=Files.readAllLines(Path.of(args[0],"inputs.txt"));
  var expected=Files.readAllLines(Path.of(args[0],"expected.txt"));
  if(input.size()!=expected.size())throw new AssertionError("case count");
  for(int c=0;c<input.size();c++){
   Scanner scan=new Scanner(input.get(c));int n=scan.nextInt();long p=scan.nextLong();
   long[]a=new long[n];for(int i=0;i<n;i++)a[i]=scan.nextLong();
   String want=expected.get(c).trim();
   long[]e=want.isEmpty()?new long[0]:Arrays.stream(want.split(" +")).mapToLong(Long::parseLong).toArray();
   if(!Arrays.equals(Main.solve(a,p),e))throw new AssertionError(args[0]+": case "+c);
  }
  System.out.println(args[0]+": "+input.size()+" passed");
 }
}
"""


def check(language, draft, directory, host_compiler=None):
    directory.mkdir()
    for exercise in draft.exercises:
        folder = directory / exercise.id
        folder.mkdir()
        variant = next(x for x in exercise.variants if x.language == language)
        filename = {"python": "reference.py", "cpp": "reference.cpp", "java": "Main.java"}[language]
        (folder / filename).write_text(variant.reference_solution, encoding="utf-8", newline="\n")
        inputs = "\n".join(" ".join(x.input.split()) for x in exercise.tests) + "\n"
        expected = "\n".join(" ".join(x.expected.split()) for x in exercise.tests) + "\n"
        (folder / "inputs.txt").write_text(inputs, encoding="utf-8", newline="\n")
        (folder / "expected.txt").write_text(expected, encoding="utf-8", newline="\n")
        smoke = next(case for case in exercise.tests if int(case.input.split()[0]) > 0)
        (folder / "smoke.in").write_text(smoke.input, encoding="utf-8", newline="\n")
        (folder / "smoke.out").write_text(smoke.expected, encoding="utf-8", newline="\n")
        (folder / "cases.json").write_text(
            json.dumps([x.model_dump() for x in exercise.tests]), encoding="utf-8"
        )
        if language == "cpp":
            (folder / "harness.cpp").write_text(CPP_HARNESS, encoding="utf-8", newline="\n")
        elif language == "java":
            (folder / "Harness.java").write_text(JAVA_HARNESS, encoding="utf-8", newline="\n")
    if host_compiler is not None:
        if language == "python":
            raise ValueError("Host compiler applies only to C++20/Java 21")
        compiler = Path(host_compiler).resolve(strict=True)
        environment = {
            **os.environ,
            "PATH": str(compiler.parent) + os.pathsep + os.environ.get("PATH", ""),
        }
        version = subprocess.run(
            [str(compiler), "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            env=environment,
        ).stdout.splitlines()[0]
        for folder in sorted(directory.iterdir()):
            if language == "cpp":
                executable = directory / ("reference.exe" if os.name == "nt" else "reference")
                cli = directory / ("cli.exe" if os.name == "nt" else "cli")
                compilation = [
                    str(compiler),
                    "-std=c++20",
                    "-O2",
                    str(folder / "harness.cpp"),
                    "-o",
                    str(executable),
                ]
                run = [str(executable), str(folder)]
                cli_compilation = [
                    str(compiler),
                    "-std=c++20",
                    "-O2",
                    str(folder / "reference.cpp"),
                    "-o",
                    str(cli),
                ]
                cli_run = [str(cli)]
            else:
                java = compiler.parent / ("java.exe" if os.name == "nt" else "java")
                compilation = [
                    str(compiler),
                    "--release",
                    "21",
                    "-d",
                    str(directory),
                    str(folder / "Main.java"),
                    str(folder / "Harness.java"),
                ]
                run = [str(java), "-cp", str(directory), "Harness", str(folder)]
                cli_compilation = None
                cli_run = [str(java), "-cp", str(directory), "Main"]
            for command in (compilation, run, cli_compilation):
                if command is not None:
                    subprocess.run(
                        command,
                        check=True,
                        capture_output=True,
                        text=True,
                        timeout=30,
                        env=environment,
                    )
            smoke = subprocess.run(
                cli_run,
                input=(folder / "smoke.in").read_text(),
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
                env=environment,
            )
            if smoke.stdout.split() != (folder / "smoke.out").read_text().split():
                raise RuntimeError(f"{language}: {folder.name} CLI smoke failed")
        return dict(
            language=language,
            compiler=version,
            environment="trusted_host_reference_check",
            target="C++20" if language == "cpp" else "Java 21",
            variants=len(draft.exercises),
            cases=sum(len(x.tests) for x in draft.exercises),
            cli_smoke_cases=len(draft.exercises),
            passed=True,
            limitation="Trusted committed source only; no execution worker, containment proof, or human review",
        )
    if language == "python":
        (directory / "harness.py").write_text(PYTHON_HARNESS, encoding="utf-8", newline="\n")
        command = ["python", "/draft/harness.py"]
    elif language == "cpp":
        command = [
            "sh",
            "-ec",
            'g++ --version; for d in /draft/*; do g++ -std=c++20 -O2 "$d/harness.cpp" -o /tmp/reference; /tmp/reference "$d"; g++ -std=c++20 -O2 "$d/reference.cpp" -o /tmp/cli; /tmp/cli < "$d/smoke.in" > /tmp/output; cmp /tmp/output "$d/smoke.out"; done',
        ]
    else:
        command = [
            "sh",
            "-ec",
            'export JAVA_TOOL_OPTIONS="-XX:-UseContainerSupport -Xmx128m"; java -version; for d in /draft/*; do mkdir -p /tmp/classes; javac --release 21 -d /tmp/classes "$d/Main.java" "$d/Harness.java"; java -cp /tmp/classes Harness "$d"; java -cp /tmp/classes Main < "$d/smoke.in" > /tmp/output; cmp /tmp/output "$d/smoke.out"; done',
        ]
    # Resolve the actual local image digest; do not silently pull a changed tag.
    inspection = subprocess.run(
        ["docker", "image", "inspect", IMAGES[language]],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    immutable = json.loads(inspection.stdout)[0]["RepoDigests"][0]
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=128",
            "--memory=1g",
            "--cpus=2",
            "--user=65534:65534",
            "--tmpfs=/tmp:rw,exec,size=256m",
            "--mount",
            f"type=bind,source={directory},target=/draft,readonly",
            immutable,
            *command,
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode:
        raise RuntimeError(
            f"{language} reference verification failed:\n{result.stdout}\n{result.stderr}"
        )
    # Compact persisted result; sources and private test vectors stay in authoring storage.
    return dict(
        language=language,
        image=immutable,
        variants=len(draft.exercises),
        cases=sum(len(x.tests) for x in draft.exercises),
        cli_smoke_cases=len(draft.exercises) if language != "python" else 0,
        passed=True,
        limitation="C++/Java batch harness checks solve plus one CLI smoke per variant; no execution-worker integration or human review",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=list(IMAGES), required=True)
    parser.add_argument(
        "--host-compiler",
        help="Optional compiler path for trusted local C++20/Java 21 reference checks",
    )
    args = parser.parse_args()
    draft = PilotDraft.model_validate_json(DRAFT.read_text(encoding="utf-8"))
    cache = ROOT / ".cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="m7-references-", dir=cache) as temporary:
        result = check(args.language, draft, Path(temporary) / args.language, args.host_compiler)
    report = dict(
        version="m7_pilot_reference_checks_1.0.0",
        draft_digest=draft.report()["draft_digest"],
        scope="trusted_original_references_only",
        runtime_acceptance=False,
        result=result,
    )
    (cache / f"m7-pilot-{args.language}-references.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
