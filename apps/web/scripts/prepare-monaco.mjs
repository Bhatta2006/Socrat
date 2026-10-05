import { cpSync, existsSync, mkdirSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';

const require = createRequire(import.meta.url);
// Monaco vendors a sanitizer copy; replacing only npm's dependency leaves that copy unpatched.
const patchedSanitizer = { name: 'patched-dompurify', setup(bundler) {
  bundler.onResolve({ filter: /\/dompurify\/dompurify\.js$/ }, () => ({ path: require.resolve('dompurify') }));
} };
let source = path.dirname(require.resolve('monaco-editor'));
while (!existsSync(path.join(source, 'package.json'))) {
  const parent = path.dirname(source);
  if (parent === source) throw new Error('Monaco package root is missing');
  source = parent;
}
const web = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const destination = path.resolve(web, 'public', 'monaco');
if (path.relative(web, destination) !== path.join('public', 'monaco')) throw new Error('Invalid generated asset directory');
rmSync(destination, { recursive: true, force: true });
mkdirSync(destination, { recursive: true });
await build({ entryPoints: { editor: path.join(web, 'scripts', 'monaco-entry.mjs') },
  outdir: destination, bundle: true, format: 'esm', splitting: true, minify: true,
  loader: { '.ttf': 'file' }, plugins: [patchedSanitizer], target: 'es2022' });
await build({ entryPoints: [path.join(source, 'esm', 'vs', 'editor', 'editor.worker.js')],
  outfile: path.join(destination, 'editor.worker.js'), bundle: true, format: 'esm', minify: true,
  plugins: [patchedSanitizer], target: 'es2022' });
cpSync(path.join(source, 'LICENSE'), path.join(web, 'public', 'monaco', 'LICENSE'));
