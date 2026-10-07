import { test } from 'node:test';
import assert from 'node:assert/strict';
import { parseDiagnostics } from '../apps/web/src/components/code-editor/diagnostics.ts';

test('Python SyntaxError and traceback map real solution.py lines', () => {
  assert.deepEqual(parseDiagnostics('Traceback (most recent call last):\n  File "C:\\Temp\\socrat-job\\solution.py", line 2\n    def broken(:\n               ^\nSyntaxError: invalid syntax'), [{line:2,severity:'error',message:'SyntaxError: invalid syntax'}]);
  assert.deepEqual(parseDiagnostics('Traceback (most recent call last):\n  File "/tmp/socrat-job/solution.py", line 3, in <module>\n    raise ValueError("bad")\nValueError: bad'), [{line:3,severity:'error',message:'ValueError: bad'}]);
});
test('GNU C++ output maps file, line, column and warning severity', () => {
  assert.deepEqual(parseDiagnostics('C:\\Temp\\solution.cpp:2:12: error: ‘invalid_symbol’ was not declared in this scope\nsolution.cpp:4:1: warning: unused variable'), [{line:2,column:12,severity:'error',message:'‘invalid_symbol’ was not declared in this scope'},{line:4,column:1,severity:'warning',message:'unused variable'}]);
});
test('javac and JVM stack frames map Solution.java', () => {
  assert.deepEqual(parseDiagnostics('C:\\Temp\\Solution.java:2: error: not a statement\ninvalid_symbol;\n^'), [{line:2,severity:'error',message:'not a statement'}]);
  assert.deepEqual(parseDiagnostics('Exception in thread "main" java.lang.RuntimeException: real traceback\n\tat Solution.main(Solution.java:2)'), [{line:2,severity:'error',message:'Runtime error at this line'}]);
});
test('unrelated paths and duplicate case diagnostics are excluded', () => {
  assert.deepEqual(parseDiagnostics('server.py:1: error: private\nsolution.cpp:2:8: error: broken\nsolution.cpp:2:8: error: broken'), [{line:2,column:8,severity:'error',message:'broken'}]);
});
