import * as monaco from 'monaco-editor/editor/editor.main.js';

globalThis.MonacoEnvironment = {
  getWorker: () => new Worker('/monaco/editor.worker.js', { type: 'module' }),
};
globalThis.monaco = monaco;
