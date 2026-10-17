/**
 * In-browser code runner. Python runs in Pyodide and C++ in Clang compiled to WebAssembly,
 * each in a Web Worker, so nothing leaves the learner's machine except output digests.
 * The page enforces the time limit by terminating a worker that runs too long.
 */
import type { BrowserTask } from '@/lib/types';

export type BrowserCase = {
  index: number;
  status: 'executed' | 'compile_error' | 'runtime_error' | 'timeout' | 'output_limit';
  digest: string;
  wall_ms: number;
  stdout: string;
  stderr: string;
};

/** `downloading:<percent>` while the C++ compiler downloads (once per browser). */
export type RunnerStage = 'loading' | 'compiling' | 'running' | `downloading:${number}`;
type Manifest = { pyodide: string; clang: string; wasi: string };
type Message = { type: string; [key: string]: unknown };

/** After this many timeouts, the remaining tests are not run (each restart costs a reload). */
const MAX_RESTARTS = 2;

let manifest: Promise<Manifest> | null = null;
function runtimes(): Promise<Manifest> {
  manifest ??= fetch('/runtimes/manifest.json').then(r => {
    if (!r.ok) throw new Error('The code runner is not installed on this server.');
    return r.json() as Promise<Manifest>;
  });
  manifest.catch(() => { manifest = null; });
  return manifest;
}

function spawn(name: string) {
  return new Worker(`/runner/${name}.worker.js`, { type: 'module', name: `socrat-${name}` });
}

/** Long-lived workers: the Python interpreter and the C++ compiler load once per tab. */
const idle: { python?: Worker; compiler?: Worker } = {};

function take(kind: 'python' | 'compiler') {
  const worker = idle[kind] ?? spawn(kind === 'python' ? 'python' : 'cpp-compile');
  idle[kind] = undefined;
  return worker;
}

function release(kind: 'python' | 'compiler', worker: Worker) {
  if (idle[kind]) worker.terminate();
  else idle[kind] = worker;
}

/** Start loading a language's runtime in the background (the Python interpreter is small). */
export async function warm(language: string) {
  if (language !== 'python' || idle.python) return;
  try {
    const { pyodide } = await runtimes();
    const worker = spawn('python');
    worker.postMessage({ type: 'warm', base: pyodide });
    idle.python = worker;
  } catch {
    /* warm-up is best effort */
  }
}

/** Runs tests in a worker, restarting it after a timeout, until every test has a result. */
async function runTests(
  make: () => Worker,
  start: (worker: Worker, tests: BrowserTask['tests']) => void,
  task: BrowserTask,
  onStage: (stage: RunnerStage) => void,
  keep?: (worker: Worker) => void,
): Promise<BrowserCase[]> {
  const results: BrowserCase[] = [];
  let restarts = 0;
  while (results.length < task.tests.length) {
    const pending = task.tests.slice(results.length);
    if (restarts > MAX_RESTARTS) {
      for (const t of pending) results.push({ index: t.index, status: 'timeout', digest: '', wall_ms: task.time_limit_ms, stdout: '', stderr: 'Not run: earlier tests ran out of time.' });
      break;
    }
    const worker = make();
    const outcome = await new Promise<'done' | 'timeout'>((resolve, reject) => {
      let timer: ReturnType<typeof setTimeout> | null = null;
      const clear = () => { if (timer) clearTimeout(timer); timer = null; };
      worker.onerror = event => { clear(); reject(new Error(event.message || 'The code runner crashed.')); };
      worker.onmessage = ({ data }: MessageEvent<Message>) => {
        if (data.type === 'ready') onStage('running');
        else if (data.type === 'start') {
          clear();
          timer = setTimeout(() => {
            results.push({ index: data.index as number, status: 'timeout', digest: '', wall_ms: task.time_limit_ms, stdout: '', stderr: `Time limit exceeded (${task.time_limit_ms} ms in the browser).` });
            resolve('timeout');
          }, task.time_limit_ms);
        } else if (data.type === 'case') {
          clear();
          const { index, status, digest, wall_ms, stdout, stderr } = data as unknown as BrowserCase;
          results.push({ index, status, digest, wall_ms, stdout, stderr });
        } else if (data.type === 'done') {
          clear();
          resolve('done');
        } else if (data.type === 'failed') {
          clear();
          reject(new Error(String(data.message)));
        }
      };
      start(worker, pending);
    });
    if (outcome === 'timeout') {
      worker.terminate();
      restarts += 1;
    } else if (keep) keep(worker);
    else worker.terminate();
  }
  return results;
}

function compile(base: string, source: string, onStage: (stage: RunnerStage) => void): Promise<{ wasm?: Uint8Array; stderr?: string }> {
  const worker = take('compiler');
  return new Promise((resolve, reject) => {
    worker.onerror = event => { worker.terminate(); reject(new Error(event.message || 'The C++ compiler crashed.')); };
    worker.onmessage = ({ data }: MessageEvent<Message>) => {
      if (data.type === 'progress') onStage((data.percent as number) < 100 ? `downloading:${data.percent as number}` : 'compiling');
      else if (data.type === 'compiled') { release('compiler', worker); resolve({ wasm: data.wasm as Uint8Array }); }
      else if (data.type === 'compile_error') { release('compiler', worker); resolve({ stderr: String(data.stderr) }); }
      else if (data.type === 'failed') { worker.terminate(); reject(new Error(String(data.message))); }
    };
    worker.postMessage({ type: 'compile', base, source });
  });
}

/** Runs a browser task and returns one result per test, in order. */
export async function runInBrowser(task: BrowserTask, source: string, onStage: (stage: RunnerStage) => void): Promise<BrowserCase[]> {
  const paths = await runtimes();
  onStage('loading');
  if (task.language === 'python') {
    let first = true;
    return runTests(
      () => (first ? ((first = false), take('python')) : spawn('python')),
      (worker, tests) => worker.postMessage({ type: 'run', base: paths.pyodide, source, tests }),
      task,
      onStage,
      worker => release('python', worker),
    );
  }
  if (task.language === 'cpp') {
    onStage('compiling');
    const built = await compile(paths.clang, source, onStage);
    if (!built.wasm) {
      return task.tests.map(t => ({ index: t.index, status: 'compile_error', digest: '', wall_ms: 0, stdout: '', stderr: built.stderr ?? '' }));
    }
    const wasm = built.wasm;
    return runTests(
      () => spawn('wasi-run'),
      (worker, tests) => worker.postMessage({ base: paths.wasi, wasm, tests }),
      task,
      onStage,
    );
  }
  throw new Error(`${task.language} cannot run in the browser.`);
}
