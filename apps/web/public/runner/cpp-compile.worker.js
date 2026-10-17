// Compiles C++20 to a WASI module with YoWASP Clang (LLVM built for WebAssembly).
// The compiler (about 100 MB) is downloaded once and then served from the browser cache.

// libc++ has no <bits/stdc++.h>; competitive programmers expect it.
const STDCPP = [
  'algorithm', 'array', 'bit', 'bitset', 'cassert', 'cctype', 'cfloat', 'chrono', 'climits', 'cmath',
  'complex', 'cstdint', 'cstdio', 'cstdlib', 'cstring', 'deque', 'functional', 'iomanip', 'iostream',
  'istream', 'iterator', 'limits', 'list', 'map', 'memory', 'numbers', 'numeric', 'optional', 'ostream',
  'queue', 'random', 'ranges', 'set', 'span', 'sstream', 'stack', 'string', 'string_view', 'tuple',
  'type_traits', 'unordered_map', 'unordered_set', 'utility', 'variant', 'vector',
].map(h => `#include <${h}>`).join('\n');

// The WASI libc++ is built without exceptions. A throw ends the program with a clear message
// instead of failing to link.
const EXCEPTIONS = `#include <cstdio>
#include <cstdlib>
#include <cstddef>
extern "C" {
void* __cxa_allocate_exception(size_t n) { return std::malloc(n); }
[[noreturn]] void __cxa_throw(void*, void*, void (*)(void*)) {
  std::fflush(stdout);
  std::fputs("terminate called after throwing an exception (exceptions are not supported in the browser runner)\\n", stderr);
  std::abort();
}
void* __cxa_begin_catch(void* e) { return e; }
void __cxa_end_catch() {}
}
`;

let clang = null;
let lastPercent = -1;
// Download progress for the page instead of the package's console logging.
function fetchProgress({ totalLength, doneLength }) {
  const percent = totalLength ? Math.floor((100 * doneLength) / totalLength) : 0;
  if (percent !== lastPercent) self.postMessage({ type: 'progress', percent });
  lastPercent = percent;
}

self.onmessage = async ({ data }) => {
  try {
    clang ??= await import(`${data.base}/bundle.js`);
    await clang.runClang(null, {}, { fetchProgress });
    if (data.type === 'warm') return void self.postMessage({ type: 'ready' });
    const files = {
      'solution.cpp': data.source,
      'socrat_eh.cpp': EXCEPTIONS,
      include: { bits: { 'stdc++.h': STDCPP } },
    };
    let stderr = '';
    const decoder = new TextDecoder();
    const collect = bytes => { if (bytes) stderr += decoder.decode(bytes, { stream: true }); };
    const started = performance.now();
    try {
      const out = await clang.runClang(
        [
          'clang++', '-std=c++20', '-O2', '-Iinclude', '-w',
          'solution.cpp', 'socrat_eh.cpp', '-o', 'solution.wasm',
          // 64 MB of stack for deep recursion; memory may grow to 1 GB.
          '-Wl,-z,stack-size=67108864', '-Wl,--max-memory=1073741824',
        ],
        files,
        { stdout: collect, stderr: collect, fetchProgress },
      );
      self.postMessage({ type: 'compiled', wasm: out['solution.wasm'], ms: Math.round(performance.now() - started) });
    } catch (error) {
      self.postMessage({ type: 'compile_error', stderr: stderr || String(error?.message || error) });
    }
  } catch (error) {
    self.postMessage({ type: 'failed', message: String(error?.message || error) });
  }
};
