# ADR 0007: CodeMirror and native development execution

Status: implementation in progress. Date: 2026-10-07.

The audited editor is Monaco 0.57.0, built by esbuild into public/monaco. It is a maintained editor, not a custom textarea implementation. The workspace downloads its generated module and language chunks when opened. Its preparation runs before every development server and production build.

Use CodeMirror 6 with first-party Python, C++ and Java packages, exact versions recorded in package.json and the npm lockfile. A small React host owns EditorView and compartments; CodeMirror owns selection, syntax, undo, indentation, search, completion and accessibility. No external editor service or CDN is involved. Independent and assessment attempts disable completion. The controlled interface remains independent of the implementation.

Remove Monaco rather than maintain two editors, two theme systems and a public asset preparation pipeline for a single-file learning workspace. An advanced editor preference has no supported second implementation; do not show a non-functional preference. Ace, Theia and cloud IDEs add no required capability. Merge views are deferred until an actual repair comparison requires them.

## Measurements

Paired production builds measured on this Windows machine using scripts/demo/measure-editor.mjs, Chromium, three fresh browser contexts, and the same diagnostic implementation fixture. Byte counts are actual downloaded JavaScript response-body bytes, uncompressed, from navigation through editor readiness, including shared route code. These are editor measurements, not execution benchmarks.

| Editor | JavaScript bytes per load | Navigation to editor, three runs | Median |
|---|---:|---|---:|
| Monaco 0.57.0 | 4,963,761 | 2,450 / 521 / 570 ms | 570 ms |
| CodeMirror 6 | 1,169,363 | 2,052 / 1,051 / 1,062 ms | 1,062 ms |

CodeMirror saves 3,794,398 bytes (76.4%) in this route-to-editor flow. It is **not faster** in these recorded timings. Both implementations defer editor downloads until opening the editor. The first run also includes cold browser/server effects; three runs are too few to infer a stable latency distribution. Raw records: .cache/editor-monaco.json and .cache/editor-codemirror.json. The installed language 6.13.0 package imports streamparser without declaring it, so streamparser 6.0.0 is explicitly pinned rather than relying on accidental hoisting.

## Native execution

Production retains the existing gVisor Docker backend. local_process is an explicitly insecure development/test backend, requires demo mode, and uses Windows Job Objects or POSIX process groups. Job signing, server-held test oracles and result acceptance remain the existing authority. Host tools are not a production security boundary. Judge0, Piston and hosted execution infrastructure are unnecessary for this development path.
