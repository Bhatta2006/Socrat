// First-load JavaScript per route after `npm run build`, gzipped, with a budget.
//
// Turbopack's build output does not print sizes, so this reads the per-route client
// reference manifests: a route loads the root main files, the root layout's chunks and
// its page's chunks. Lazy chunks (CodeMirror, confetti) are excluded by design.
//
// Usage: node scripts/web/bundle-report.mjs [--budget-kb 300] [--json]
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { gzipSync } from 'node:zlib';

const NEXT = path.resolve('apps/web/.next');
const args = process.argv.slice(2);
const budgetKb = Number(args[args.indexOf('--budget-kb') + 1]) || 300;
const json = args.includes('--json');

if (!existsSync(path.join(NEXT, 'build-manifest.json'))) {
  console.error('No production build found. Run `npm run build` first.');
  process.exit(2);
}

const root = JSON.parse(readFileSync(path.join(NEXT, 'build-manifest.json'), 'utf8'));
// polyfillFiles load with noModule, so modern browsers never fetch them.
const rootFiles = root.rootMainFiles ?? [];
const sizes = new Map();
function gzipKb(file) {
  if (!sizes.has(file)) {
    const full = path.join(NEXT, file.replace(/^\/?_next\//, ''));
    sizes.set(file, existsSync(full) ? gzipSync(readFileSync(full)).length / 1024 : 0);
  }
  return sizes.get(file);
}

function* manifests(dir) {
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) yield* manifests(full);
    else if (name === 'page_client-reference-manifest.js') yield full;
  }
}

const rows = [];
for (const file of manifests(path.join(NEXT, 'server', 'app'))) {
  const sandbox = { globalThis: {} };
  sandbox.globalThis = sandbox;
  vm.runInNewContext(readFileSync(file, 'utf8'), sandbox);
  for (const [key, manifest] of Object.entries(sandbox.__RSC_MANIFEST)) {
    if (key.startsWith('/_')) continue; // framework error pages
    const entries = manifest.entryJSFiles ?? {};
    const page = Object.keys(entries).find(k => k.endsWith(`/app${key}`));
    const layout = Object.keys(entries).find(k => k.endsWith('/app/layout'));
    const files = new Set([...rootFiles, ...(entries[layout] ?? []), ...(entries[page] ?? [])]);
    const kb = [...files].reduce((sum, f) => sum + gzipKb(f), 0);
    rows.push({ route: key.replace(/\/page$/, '') || '/', kb: Math.round(kb * 10) / 10, chunks: files.size });
  }
}
rows.sort((a, b) => b.kb - a.kb);
const over = rows.filter(r => r.kb > budgetKb);
if (json) {
  console.log(JSON.stringify({ budgetKb, rows }, null, 2));
} else {
  console.log(`First-load JS per route (gzip), budget ${budgetKb} KB`);
  for (const r of rows) console.log(`${r.kb > budgetKb ? '!!' : '  '} ${r.route.padEnd(28)} ${String(r.kb).padStart(7)} KB  ${r.chunks} chunks`);
}
if (over.length) {
  console.error(`${over.length} route(s) over the ${budgetKb} KB budget.`);
  process.exit(1);
}
