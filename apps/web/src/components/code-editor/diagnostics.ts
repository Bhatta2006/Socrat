import type { EditorDiagnostic } from './types';

/** Parse only public compiler output; no source evaluation or HTML rendering. */
export function parseDiagnostics(output: string): EditorDiagnostic[] {
  const diagnostics: EditorDiagnostic[] = [];
  const lines = output.split(/\r?\n/);
  for (let index = 0; index < lines.length; index++) {
    const line = lines[index];
    const compiler = line.match(/(?:^|[\\/])(?:solution\.cpp|Solution\.java):(\d+):(?:(\d+):)?\s*(error|warning|fatal error):\s*(.*)/);
    if (compiler) {
      diagnostics.push({ line: Number(compiler[1]), ...(compiler[2] ? {column:Number(compiler[2])} : {}), severity: compiler[3] === 'warning' ? 'warning' : 'error', message: compiler[4] });
      continue;
    }
    const python = line.match(/File "(?:[^"\n]*[\\/])?solution\.py", line (\d+)/);
    const java = line.match(/\bat Solution(?:\.[\w$]+)?\([^)]*Solution\.java:(\d+)\)/);
    if (python || java) {
      const final = lines.slice(index+1).filter(text=>/^(?:\w+(?:Error|Exception)|java\.[\w.]+(?:Error|Exception))\b/.test(text.trim())).at(-1);
      diagnostics.push({line:Number((python ?? java)![1]), severity:'error',message: final?.trim() ?? 'Runtime error at this line'});
    }
  }
  return diagnostics.filter((item,index)=>diagnostics.findIndex(other=>other.line===item.line && other.column===item.column && other.message===item.message)===index);
}
