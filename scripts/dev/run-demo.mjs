import { spawn } from 'node:child_process';
const windows = process.platform === 'win32';
const child = spawn(windows ? 'powershell.exe' : 'bash', windows ? ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', 'scripts/dev/start-demo.ps1', ...process.argv.slice(2)] : ['scripts/dev/start-demo.sh', ...process.argv.slice(2)], { stdio: 'inherit' });
child.on('exit', code => process.exit(code ?? 1));
