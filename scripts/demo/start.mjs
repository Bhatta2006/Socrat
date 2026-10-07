// One-command bootstrap. Only Docker and Node are needed on the host.
import { spawnSync, spawn } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { mkdirSync, writeFileSync, readFileSync, existsSync } from 'node:fs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
function docker(args, capture = false) {
  const result = spawnSync('docker', args, { cwd: root, encoding: 'utf8', timeout: args[0] === 'info' ? 60_000 : 1_800_000, stdio: capture ? 'pipe' : 'inherit' });
  if (result.error || result.status !== 0) {
    console.error(capture ? result.stderr : '', result.error?.message ?? 'Docker command failed. Start Docker Desktop with Linux containers, then retry npm run demo.');
    process.exit(1);
  }
  return capture ? result.stdout.trim() : '';
}
docker(['info', '--format', '{{.ServerVersion}}']);
const bases = { PYTHON_BASE: 'python:3.12.14-slim-bookworm', CPP_BASE: 'gcc:14-bookworm', JAVA_BASE: 'eclipse-temurin:21-jdk-noble' };
const pinned = {};
for (const [key, tag] of Object.entries(bases)) {
  docker(['pull', tag]);
  pinned[key] = JSON.parse(docker(['image', 'inspect', '--format', '{{json .RepoDigests}}', tag], true))[0];
  if (!pinned[key]?.includes('@sha256:')) throw new Error('Upstream runtime must resolve to an immutable registry digest');
}
const profiles = [];
for (const language of ['python', 'cpp', 'java']) {
  const tag = `socrat-demo-${language}:local`;
  docker(['build', '--provenance=false', '-f', `services/execution/runtime/${language}.Dockerfile`, '-t', tag,
    ...Object.entries(pinned).flatMap(([key, value]) => ['--build-arg', `${key}=${value}`]), '.']);
  const imageId = docker(['image', 'inspect', '--format', '{{.Id}}', tag], true);
  if (!/^sha256:[a-f0-9]{64}$/.test(imageId)) throw new Error('Immutable local runtime ID required');
  profiles.push({ id: `demo_${language}`, language, image: `socrat/demo-${language}@${imageId}`,
    limits: { cpu_seconds: 2, wall_seconds: 5, memory_mb: language === 'cpp' ? 512 : 256, pids: 64, output_bytes: 65536, disk_mb: 16, compile_seconds: 20 },
    attestation_reference: 'Local sample runtime; not release attested' });
}
const privatePath = path.join(root, '.cache/demo-environment.json');
const previous = existsSync(privatePath) ? JSON.parse(readFileSync(privatePath, 'utf8')) : {};
const credentials = {
  SOCRAT_EXECUTION_PROFILES: JSON.stringify(profiles),
  SOCRAT_EXECUTION_SIGNING_SECRET: previous.SOCRAT_EXECUTION_SIGNING_SECRET ?? randomBytes(48).toString('hex'),
  SOCRAT_EXECUTION_WORKER_SECRET: previous.SOCRAT_EXECUTION_WORKER_SECRET ?? randomBytes(48).toString('hex'),
};
mkdirSync(path.dirname(privatePath), { recursive: true });
writeFileSync(privatePath, JSON.stringify(credentials), { mode: 0o600 });
const environment = { ...process.env, ...credentials };
if (process.argv.includes('--prepare')) process.exit(0);
console.log('\nSocrat demo: http://localhost:3000 — starts after migrations, sample seed, API and sandbox are healthy.\n');
const child = spawn('docker', ['compose', '-f', 'compose.demo.yaml', '--profile', 'demo', 'up', '--build', ...process.argv.slice(2)],
  { cwd: root, stdio: 'inherit', env: environment });
child.on('error', error => { console.error(error.message); process.exitCode = 1; });
child.on('exit', code => { process.exitCode = code ?? 1; });
