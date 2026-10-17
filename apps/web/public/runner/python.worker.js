// Runs Python solutions with Pyodide. One interpreter per worker; every test gets a fresh
// __main__ namespace and its own stdin. The page terminates the worker on a timeout.
import { report } from './common.js';

let runner = null;

const PRELUDE = `
import sys, io, traceback
# Solutions run on the learner's own machine; keep them away from the browser APIs.
for _name in ("js", "pyodide", "pyodide_js", "pyodide.ffi", "pyodide.http"):
    sys.modules[_name] = None

def __socrat_run(src, data):
    out, err = io.StringIO(), io.StringIO()
    saved = sys.stdin, sys.stdout, sys.stderr
    sys.stdin = io.TextIOWrapper(io.BytesIO(data.encode()), encoding="utf-8")
    sys.stdout, sys.stderr = out, err
    failed = False
    try:
        exec(compile(src, "solution.py", "exec"), {"__name__": "__main__"})
    except SystemExit as e:
        failed = e.code not in (None, 0)
    except BaseException:
        traceback.print_exc()
        failed = True
    finally:
        sys.stdin, sys.stdout, sys.stderr = saved
        sys.setrecursionlimit(1000)
    return failed, out.getvalue(), err.getvalue()
`;

async function load(base) {
  if (runner) return runner;
  const { loadPyodide } = await import(`${base}/pyodide.mjs`);
  const py = await loadPyodide({ indexURL: `${base}/`, stdout: () => {}, stderr: () => {} });
  py.runPython(PRELUDE);
  runner = { py, run: py.globals.get('__socrat_run') };
  return runner;
}

self.onmessage = async ({ data }) => {
  try {
    const { run } = await load(data.base);
    if (data.type === 'warm') return void self.postMessage({ type: 'ready' });
    self.postMessage({ type: 'ready' });
    for (const test of data.tests) {
      self.postMessage({ type: 'start', index: test.index });
      const started = performance.now();
      const result = run(data.source, test.input);
      const [failed, stdout, stderr] = result.toJs();
      result.destroy();
      self.postMessage(await report(test.index, failed ? 'runtime_error' : 'executed', stdout, stderr, started));
    }
    self.postMessage({ type: 'done' });
  } catch (error) {
    self.postMessage({ type: 'failed', message: String(error?.message || error) });
  }
};
