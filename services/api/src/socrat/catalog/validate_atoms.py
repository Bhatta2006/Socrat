"""Compile and run trusted authored adapters; never translate learner code."""

import os
import subprocess
import tempfile
from pathlib import Path

from socrat.catalog.atoms import Adapter


def check_adapter(language: str, adapter: Adapter, tools: dict[str, list[str]]) -> None:
    if adapter.expected is None:
        raise ValueError("runnable adapters need a reviewed expected output")
    if language not in tools:
        raise ValueError(f"{language}: toolchain unavailable")
    with tempfile.TemporaryDirectory(prefix="socrat-atom-") as directory:
        root = Path(directory)
        env = {
            **os.environ,
            "PATH": str(Path(tools[language][0]).parent) + os.pathsep + os.environ.get("PATH", ""),
        }
        suffix = ".exe" if os.name == "nt" else ""
        if language == "python":
            source = root / "example.py"
            source.write_text(adapter.code, encoding="utf-8")
            command = [tools[language][0], "-I", str(source)]
        else:
            source = root / ("example.cpp" if language == "cpp" else "Solution.java")
            source.write_text(adapter.code, encoding="utf-8")
            compile_command = (
                [
                    tools[language][0],
                    "-std=c++20",
                    str(source),
                    "-o",
                    str(root / ("example" + suffix)),
                ]
                if language == "cpp"
                else [tools[language][0], str(source)]
            )
            compiled = subprocess.run(
                compile_command, capture_output=True, cwd=root, env=env, timeout=30
            )
            if compiled.returncode:
                raise ValueError(
                    f"{language}: compile failed: {compiled.stderr.decode(errors='replace')[-1200:]}"
                )
            command = (
                [str(root / ("example" + suffix))]
                if language == "cpp"
                else [tools[language][1], "-cp", str(root), "Solution"]
            )
        result = subprocess.run(
            command, input=adapter.stdin.encode(), capture_output=True, cwd=root, env=env, timeout=5
        )
        actual = result.stdout.decode(errors="replace").replace("\r\n", "\n").rstrip()
        if result.returncode or actual != adapter.expected.replace("\r\n", "\n").rstrip():
            raise ValueError(f"{language}: example output disagrees with its reviewed output")
