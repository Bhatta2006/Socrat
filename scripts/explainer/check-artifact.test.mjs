import test from 'node:test';
import assert from 'node:assert/strict';
import { inspectScripts } from './check-artifact.mjs';

test('allows ordinary visual computations and rejects nested browser capabilities', () => {
  inspectScripts(['const nums=[1,2];function draw(i){return nums[i]*2} window.__explainer={step:draw};']);
  inspectScripts(['const color=window.getComputedStyle(document.documentElement).getPropertyValue("--primary");']);
  inspectScripts(['class Scene { constructor(){this.index=0} step(i){this.index=i} }']);
  for (const script of [
    'function f(){fetch("/secret")}', 'const f=()=>new Function("return 1")',
    'window.parent.document', 'document.cookie', 'const x=({}).constructor',
    'import("https://example.com")', 'const x=localStorage.getItem("key")',
    'while(true){}', 'while(1){}', 'for(;;){}', 'setTimeout("alert(1)",10)',
    'document.defaultView', 'const f=()=>new Worker("x")',
    'class Scene { step(){return this.constructor} }',
  ]) assert.throws(() => inspectScripts([script]), undefined, script);
});
