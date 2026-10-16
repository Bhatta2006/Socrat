"""Run many statement snippets per language with one compile (authoring runner, D7).

Quiz snippets are statement blocks, like the existing items' code (``cout << i`` with no
``main``). The harness wraps each in its own function inside one program per language,
compiles once, and runs them in order, printing a marker line before each. A crash or
timeout loses only the snippet it happened in: the run resumes after it.

This is trusted authoring code run with local toolchains, never learner code.
"""

import os
import subprocess
import tempfile
import textwrap
from dataclasses import dataclass
from pathlib import Path

MARK = "\x1e"
PYTHON_PREAMBLE = "import sys\n"
CPP_PREAMBLE = "#include <bits/stdc++.h>\nusing namespace std;\n"
JAVA_PREAMBLE = "import java.util.*;\n"


@dataclass(frozen=True)
class Result:
    output: str | None  # None when the snippet failed
    error: str | None = None


def python_source(snippets: list[str]) -> str:
    parts = [PYTHON_PREAMBLE]
    for i, code in enumerate(snippets):
        parts.append(f"def _s{i}():\n{textwrap.indent(code.rstrip() or 'pass', '    ')}\n")
    names = ", ".join(f"_s{i}" for i in range(len(snippets)))
    parts.append(
        f"_ITEMS = [{names}]\n"
        "_START = int(sys.argv[1]) if len(sys.argv) > 1 else 0\n"
        "for _i in range(_START, len(_ITEMS)):\n"
        f"    print('{MARK}%d' % _i, flush=True)\n"
        "    try:\n"
        "        _ITEMS[_i]()\n"
        "    except Exception as _e:\n"
        f"        print('{MARK}ERR ' + type(_e).__name__, flush=True)\n"
        "    sys.stdout.flush()\n"
    )
    return "\n".join(parts)


def cpp_source(snippets: list[str]) -> str:
    parts = [CPP_PREAMBLE]
    for i, code in enumerate(snippets):
        parts.append(f"void _s{i}() {{\n{textwrap.indent(code.rstrip(), '    ')}\n}}\n")
    names = ", ".join(f"_s{i}" for i in range(len(snippets)))
    parts.append(
        "int main(int argc, char** argv) {\n"
        f"    void (*items[])() = {{{names}}};\n"
        f"    int count = {len(snippets)};\n"
        "    int start = argc > 1 ? atoi(argv[1]) : 0;\n"
        "    for (int i = start; i < count; i++) {\n"
        f'        cout << "\\x1e" << i << "\\n" << flush;\n'
        "        items[i]();\n"
        "        cout << flush;\n"
        "    }\n"
        "}\n"
    )
    return "\n".join(parts)


def java_source(snippets: list[str]) -> str:
    parts = [JAVA_PREAMBLE, "public class Solution {"]
    for i, code in enumerate(snippets):
        parts.append(f"static void _s{i}() {{\n{textwrap.indent(code.rstrip(), '    ')}\n}}")
    names = ", ".join(f"Solution::_s{i}" for i in range(len(snippets)))
    parts.append(
        "public static void main(String[] args) {\n"
        f"    Runnable[] items = {{{names}}};\n"
        "    int start = args.length > 0 ? Integer.parseInt(args[0]) : 0;\n"
        "    for (int i = start; i < items.length; i++) {\n"
        '        System.out.println("\\u001e" + i);\n'
        "        try { items[i].run(); }\n"
        '        catch (Throwable t) { System.out.println("\\u001eERR " + t.getClass().getSimpleName()); }\n'
        "        System.out.flush();\n"
        "    }\n"
        "}\n}"
    )
    return "\n".join(parts)


SOURCES = {"python": python_source, "cpp": cpp_source, "java": java_source}
FILES = {"python": "batch.py", "cpp": "batch.cpp", "java": "Solution.java"}


def parse(stdout: str) -> tuple[dict[int, Result], int | None, str]:
    """Closed results, plus the index and output of the last block (still open)."""
    results: dict[int, Result] = {}
    current: int | None = None
    lines: list[str] = []
    for line in stdout.replace("\r\n", "\n").split("\n"):
        if line.startswith(MARK + "ERR"):
            if current is not None:
                results[current] = Result(None, line[len(MARK) :].strip())
            current, lines = None, []
        elif line.startswith(MARK) and line[1:].isdigit():
            if current is not None:
                results[current] = Result("\n".join(lines).rstrip())
            current, lines = int(line[1:]), []
        elif current is not None:
            lines.append(line)
    return results, current, "\n".join(lines).rstrip()


class Runner:
    """Compiles and runs snippet batches with the host toolchains."""

    def __init__(self, tools: dict[str, list[str]], timeout: float = 20.0):
        self.tools = tools
        self.timeout = timeout

    def env(self, language: str, **extra: str) -> dict[str, str]:
        path = str(Path(self.tools[language][0]).parent)
        return {**os.environ, "PATH": path + os.pathsep + os.environ.get("PATH", ""), **extra}

    def compile(self, language: str, root: Path, snippets: list[str]) -> str | None:
        """Writes and compiles the batch; returns the compiler error, if any."""
        source = root / FILES[language]
        source.write_text(SOURCES[language](snippets), encoding="utf-8")
        if language == "python":
            command = [self.tools["python"][0], "-I", "-m", "py_compile", str(source)]
        elif language == "cpp":
            exe = root / ("batch.exe" if os.name == "nt" else "batch")
            command = [self.tools["cpp"][0], "-std=c++20", "-O1", str(source), "-o", str(exe)]
        else:
            command = [self.tools["java"][0], "-nowarn", str(source)]
        done = subprocess.run(
            command, capture_output=True, cwd=root, env=self.env(language), timeout=120
        )
        if done.returncode:
            return (done.stderr or done.stdout).decode(errors="replace")[-1500:]
        return None

    def command(self, language: str, root: Path, start: int) -> list[str]:
        if language == "python":
            # -P/-s instead of -I so PYTHONHASHSEED applies: two seeds expose hash-order output.
            return [self.tools["python"][0], "-P", "-s", str(root / FILES["python"]), str(start)]
        if language == "cpp":
            return [str(root / ("batch.exe" if os.name == "nt" else "batch")), str(start)]
        return [self.tools["java"][1], "-Xss16m", "-cp", str(root), "Solution", str(start)]

    def execute(
        self, language: str, root: Path, count: int, hash_seed: str = "0"
    ) -> dict[int, Result]:
        results: dict[int, Result] = {}
        start = 0
        while start < count:
            try:
                done = subprocess.run(
                    self.command(language, root, start),
                    capture_output=True,
                    cwd=root,
                    env=self.env(language, PYTHONHASHSEED=hash_seed),
                    timeout=self.timeout,
                )
                stdout, failure = (
                    done.stdout,
                    (f"exit {done.returncode}" if done.returncode else ""),
                )
            except subprocess.TimeoutExpired as exc:
                stdout, failure = exc.stdout or b"", "timeout"
            found, last, tail = parse(stdout.decode(errors="replace"))
            results.update(found)
            if last is None:
                if not failure:
                    break
                last = start  # stopped before any marker: the first snippet failed
            if not failure:
                results[last] = Result(tail)
                break
            # The snippet running when the process stopped failed; resume after it.
            results[last] = Result(None, failure)
            start = last + 1
        return results

    def run(self, language: str, snippets: list[str], hash_seed: str = "0") -> list[Result]:
        """One result per snippet, in order. Compile errors are isolated per snippet."""
        if not snippets:
            return []
        if language not in self.tools:
            return [Result(None, f"{language} toolchain unavailable")] * len(snippets)
        with tempfile.TemporaryDirectory(prefix="socrat-quiz-") as directory:
            root = Path(directory)
            error = self.compile(language, root, snippets)
            if error is None:
                found = self.execute(language, root, len(snippets), hash_seed)
                return [found.get(i, Result(None, "no output")) for i in range(len(snippets))]
        if len(snippets) == 1:
            return [Result(None, f"compile failed: {error}")]
        # Split to find the snippets that do not compile; the rest still run in batches.
        middle = len(snippets) // 2
        return self.run(language, snippets[:middle], hash_seed) + self.run(
            language, snippets[middle:], hash_seed
        )
