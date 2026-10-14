import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn, execFileSync } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';

test('isolated checker authenticates and validates a working visual over HTTP', { timeout: 35000 }, async () => {
  const secret = randomBytes(32).toString('hex');
  const server = spawn(process.execPath, ['scripts/explainer/checker-server.mjs'], { env: { ...process.env, PORT: '0', SOCRAT_EXPLAINER_CHECKER_SECRET: secret }, stdio: ['ignore','pipe','pipe'] });
  try {
    const port = await new Promise((resolve,reject) => {
      const timer = setTimeout(() => reject(Error('Checker startup timed out')), 5000);
      server.stdout.once('data', chunk => { clearTimeout(timer);resolve(JSON.parse(chunk).port); });
      server.once('error', reject);
    });
    const origin = `http://127.0.0.1:${port}`;
    assert.equal((await fetch(origin+'/health')).status, 200);
    assert.equal((await fetch(origin+'/check',{method:'POST',body:'{}'})).status, 403);
    const python = path.resolve('.venv', process.platform==='win32' ? 'Scripts/python.exe' : 'bin/python');
    const payload = execFileSync(python, ['-c', "import sys,json;from socrat.explainer.artifact import validate,compile_document;d=validate(sys.stdin.read());h,c=compile_document(d.html,'qa','http://host.socrat.invalid');print(json.dumps(dict(html=h,csp=c,scripts=d.scripts)))"], { input:readFileSync('services/api/tests/fixtures/visual.html'),env:{...process.env,PYTHONPATH:path.resolve('services/api/src')},encoding:'utf8' });
    const response = await fetch(origin+'/check',{method:'POST',headers:{Authorization:'Bearer '+secret,'Content-Type':'application/json'},body:payload,signal:AbortSignal.timeout(25000)});
    assert.equal(response.status,200);
    const result = await response.json();
    assert.equal(result.ok,true,result.reason);
    assert.equal(result.step_count,4);
  } finally { server.kill(); }
});
