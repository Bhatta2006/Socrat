"""Host toolchain discovery; optional languages never disable Python."""

import os
import re
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def toolchains() -> dict[str, list[str]]:
    tools = {"python": [str(Path(sys.executable).resolve())]}
    cpp_candidates = [os.environ.get("SOCRAT_CPP_COMPILER", "")]
    if os.name == "nt":
        cpp_candidates += [r"C:\msys64\ucrt64\bin\g++.exe", r"C:\msys64\mingw64\bin\g++.exe"]
    cpp_candidates += [shutil.which("g++") or ""]
    for candidate in cpp_candidates:
        if not candidate or not Path(candidate).is_file():
            continue
        try:
            check = subprocess.run(
                [candidate, "-std=c++20", "-x", "c++", "-fsyntax-only", "-"],
                input=b"int main() {}",
                capture_output=True,
                timeout=10,
                env={
                    **os.environ,
                    "PATH": str(Path(candidate).parent) + os.pathsep + os.environ.get("PATH", ""),
                },
            )
            if check.returncode == 0:
                tools["cpp"] = [str(Path(candidate).resolve())]
                break
        except (OSError, subprocess.SubprocessError):
            pass
    java_bins = []
    if os.environ.get("JAVA_HOME"):
        java_bins.append(Path(os.environ["JAVA_HOME"]) / "bin")
    if os.name == "nt":
        java_bins += sorted(Path(r"C:\Program Files\Microsoft").glob("jdk-21*/bin"), reverse=True)
    javac = shutil.which("javac")
    if javac:
        java_bins.append(Path(javac).parent)
    suffix = ".exe" if os.name == "nt" else ""
    for directory in java_bins:
        commands = [str(directory / (name + suffix)) for name in ("javac", "java")]
        try:
            versions = [
                subprocess.run([command, "-version"], capture_output=True, timeout=10)
                for command in commands
            ]
            if all(
                version.returncode == 0
                and re.search(
                    r"\b21(?:\.|\b)", (version.stdout + version.stderr).decode(errors="replace")
                )
                for version in versions
            ):
                tools["java"] = commands
                break
        except (OSError, subprocess.SubprocessError):
            pass
    return tools


def availability():
    tools = toolchains()
    return {
        language: {
            "ready": language in tools,
            "message": "Ready"
            if language in tools
            else "Not installed on this machine: run scripts\\dev\\doctor.ps1",
        }
        for language in ("python", "cpp", "java")
    }
