$ErrorActionPreference = 'Continue'
Set-Location (Resolve-Path "$PSScriptRoot/../..")
Write-Host 'Socrat native development doctor (Windows; Docker is optional)'
if (Get-Command node -ErrorAction SilentlyContinue) { node --version } else { Write-Host 'Install Node: winget install --exact --id OpenJS.NodeJS.LTS' }
if (Test-Path .venv/Scripts/python.exe) { & .venv/Scripts/python.exe --version } elseif (Get-Command python -ErrorAction SilentlyContinue) { python --version } else { Write-Host 'Install Python >=3.12: winget install --exact --id Python.Python.3.12' }
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Write-Host 'Install uv: python -m pip install uv==0.12.20' }
if (Test-Path .venv/Scripts/python.exe) {
  $env:PYTHONPATH = "$(Get-Location)/services/api/src;$(Get-Location)/services/execution/src"
  & .venv/Scripts/python.exe -c "from runner.toolchains import availability; import json; print(json.dumps(availability(), indent=2))"
}
Write-Host 'For missing C++20: winget install --exact --id MSYS2.MSYS2'
Write-Host 'Then open MSYS2 UCRT64 and run: pacman -Syu; pacman -S --needed mingw-w64-ucrt-x86_64-gcc'
Write-Host 'For missing JDK 21: winget install --exact --id Microsoft.OpenJDK.21'
Write-Host 'Default discovery includes C:\msys64\ucrt64\bin and C:\Program Files\Microsoft\jdk-21*\bin; restart the demo after installing tools.'
Write-Host 'Optional Docker: winget install --exact --id Docker.DockerDesktop'
Write-Host 'Start the native stack: npm run dev:demo'
