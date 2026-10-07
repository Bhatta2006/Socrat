#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/../.."
echo 'Socrat native doctor (Docker optional)'
node --version || echo 'Install Node 22–24 using your OS package manager.'
python3 --version || echo 'Install Python >=3.12 using your OS package manager.'
uv --version || echo 'Install uv: python3 -m pip install uv==0.12.20'
if test -x .venv/bin/python; then PYTHONPATH=services/api/src:services/execution/src .venv/bin/python -c 'from runner.toolchains import availability; import json; print(json.dumps(availability(),indent=2))'; fi
g++ --version || echo 'Debian/Ubuntu: sudo apt-get install g++; macOS: brew install gcc (set SOCRAT_CPP_COMPILER to the installed g++-N).'
javac -version || echo 'Debian/Ubuntu: sudo apt-get install openjdk-21-jdk; macOS: brew install openjdk@21 (set JAVA_HOME).'
echo 'Run npm run dev:demo. Production isolation still requires a Linux gVisor host.'
