// Runs a compiled WASI program once per test with the test as stdin. The page terminates the
// worker on a timeout and starts a new one for the remaining tests.
import { report } from './common.js';

self.onmessage = async ({ data }) => {
  try {
    const shim = await import(`${data.base}/index.js`);
    const module = await WebAssembly.compile(data.wasm);
    self.postMessage({ type: 'ready' });
    for (const test of data.tests) {
      self.postMessage({ type: 'start', index: test.index });
      const decoder = { out: new TextDecoder(), err: new TextDecoder() };
      let stdout = '';
      let stderr = '';
      const fds = [
        new shim.OpenFile(new shim.File(new TextEncoder().encode(test.input), { readonly: true })),
        new shim.ConsoleStdout(bytes => { stdout += decoder.out.decode(bytes, { stream: true }); }),
        new shim.ConsoleStdout(bytes => { stderr += decoder.err.decode(bytes, { stream: true }); }),
      ];
      const wasi = new shim.WASI(['solution'], [], fds);
      const started = performance.now();
      let status = 'executed';
      try {
        const instance = await WebAssembly.instantiate(module, { wasi_snapshot_preview1: wasi.wasiImport });
        const code = wasi.start(instance);
        if (code !== 0) {
          status = 'runtime_error';
          stderr += `\nProcess exited with code ${code}`;
        }
      } catch (error) {
        status = 'runtime_error';
        const message = String(error?.message || error);
        stderr += stderr.includes('terminate called') ? '' : `\n${/unreachable|abort/i.test(message) ? 'Program aborted' : message}`;
      }
      self.postMessage(await report(test.index, status, stdout, stderr.trim(), started));
    }
    self.postMessage({ type: 'done' });
  } catch (error) {
    self.postMessage({ type: 'failed', message: String(error?.message || error) });
  }
};
