'use client';

import { useEffect, useRef } from 'react';

const VERTEX = `
precision highp float;
attribute vec2 a_uv;
uniform float u_time;
uniform float u_aspect;
uniform vec2 u_pointer;
varying vec3 v_normal;
varying vec3 v_position;
varying vec2 v_uv;

vec3 surface(vec2 uv) {
  float t = uv.x;
  float v = uv.y * 2.0 - 1.0;
  float fold = v * 18.84956 + sin(t * 2.0 + u_time * 0.18) * 0.28;
  float spread = 0.12 + pow(max(t, 0.0), 0.72) * 6.6;
  float x = v * spread;
  float y = 1.55 - t * 4.25 + v * v * t * 1.1;
  y += pow(t, 7.0) * (0.23 * cos(fold) + 0.12);
  float z = cos(fold) * (0.07 + t * 0.64) + sin(t * 3.14159) * 0.4;
  z += sin(t * 5.0 - u_time * 0.22) * t * 0.08;
  x += u_pointer.x * z * 0.18;
  y += u_pointer.y * z * 0.1;
  return vec3(x, y, z);
}

void main() {
  vec3 p = surface(a_uv);
  vec3 du = surface(a_uv + vec2(0.001, 0.0)) - p;
  vec3 dv = surface(a_uv + vec2(0.0, 0.001)) - p;
  v_normal = normalize(cross(du, dv));
  v_position = p;
  v_uv = a_uv;
  float perspective = 1.0 + p.z * 0.07;
  gl_Position = vec4(p.x / (u_aspect * 2.7) * perspective, p.y / 2.7 * perspective, -p.z * 0.1, 1.0);
}`;

const FRAGMENT = `
precision highp float;
varying vec3 v_normal;
varying vec3 v_position;
varying vec2 v_uv;

void main() {
  vec3 n = normalize(v_normal);
  if (n.z < 0.0) n = -n;
  vec3 view = normalize(vec3(0.0, 1.0, 7.0) - v_position);
  vec3 light = normalize(vec3(-2.0, 3.5, 4.0));
  vec3 fill = normalize(vec3(3.0, -1.5, 2.0));
  float diffuse = max(dot(n, light), 0.0);
  float spec = pow(max(dot(n, normalize(light + view)), 0.0), 44.0);
  float rim = pow(1.0 - max(dot(n, view), 0.0), 2.5);
  float lowerLight = max(dot(n, fill), 0.0);
  vec3 violet = mix(vec3(0.18, 0.015, 0.58), vec3(0.49, 0.15, 0.98), diffuse);
  vec3 color = violet * (0.35 + diffuse * 0.95);
  color += vec3(0.73, 0.5, 1.0) * spec * 0.9;
  color += vec3(0.38, 0.22, 0.7) * rim * 0.5;
  color += vec3(0.34, 0.2, 0.55) * pow(lowerLight, 3.0) * smoothstep(0.35, 1.0, v_uv.x);
  float grain = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
  color += (grain - 0.5) * 0.018;
  float alpha = smoothstep(0.0, 0.16, v_uv.x);
  gl_FragColor = vec4(color, alpha);
}`;

/** A lit, folded mesh: no model download or 3D framework is needed. */
export function RibbonScene() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const stage = stageRef.current;
    if (!canvas || !stage) return;
    const gl = canvas.getContext('webgl', { alpha: true, antialias: false, powerPreference: 'low-power' });
    if (!gl) return;
    const resources: WebGLShader[] = [];
    const compile = (type: number, source: string) => {
      const shader = gl.createShader(type);
      if (!shader) return null;
      resources.push(shader);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null;
    };
    const vertex = compile(gl.VERTEX_SHADER, VERTEX);
    const fragment = compile(gl.FRAGMENT_SHADER, FRAGMENT);
    const program = gl.createProgram();
    const buffer = gl.createBuffer();
    const release = () => {
      resources.forEach(s => gl.deleteShader(s));
      if (buffer) gl.deleteBuffer(buffer);
      if (program) gl.deleteProgram(program);
      stage.removeAttribute('data-rendered');
    };
    if (!vertex || !fragment || !program || !buffer) { release(); return; }
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) { release(); return; }
    gl.useProgram(program);

    const vertices: number[] = [];
    const rows = 64;
    const columns = 144;
    for (let row = 0; row < rows; row++) {
      for (let column = 0; column < columns; column++) {
        const u = row / rows, v = column / columns;
        const nextU = (row + 1) / rows, nextV = (column + 1) / columns;
        vertices.push(u, v, nextU, v, u, nextV, u, nextV, nextU, v, nextU, nextV);
      }
    }
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(vertices), gl.STATIC_DRAW);
    const uv = gl.getAttribLocation(program, 'a_uv');
    gl.enableVertexAttribArray(uv);
    gl.vertexAttribPointer(uv, 2, gl.FLOAT, false, 0, 0);
    gl.enable(gl.DEPTH_TEST);
    gl.clearColor(0, 0, 0, 0);
    const time = gl.getUniformLocation(program, 'u_time');
    const aspect = gl.getUniformLocation(program, 'u_aspect');
    const pointerUniform = gl.getUniformLocation(program, 'u_pointer');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    let visible = true;
    let frame = 0;
    let last = 0;
    let stopped = false;
    const pointer = { x: 0, y: 0, targetX: 0, targetY: 0 };
    const draw = (now: number) => {
      if (stopped) return;
      const moving = !reduced.matches && visible && !document.hidden;
      if (now - last > 32 || !moving) {
        pointer.x += (pointer.targetX - pointer.x) * 0.06;
        pointer.y += (pointer.targetY - pointer.y) * 0.06;
        gl.uniform1f(time, reduced.matches ? 0 : now * 0.001);
        gl.uniform2f(pointerUniform, reduced.matches ? 0 : pointer.x, reduced.matches ? 0 : pointer.y);
        gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
        gl.drawArrays(gl.TRIANGLES, 0, vertices.length / 2);
        stage.setAttribute('data-rendered', 'true');
        last = now;
      }
      frame = moving ? requestAnimationFrame(draw) : 0;
    };
    const resume = () => { if (!frame && !stopped) frame = requestAnimationFrame(draw); };
    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 1.25);
      canvas.width = Math.max(1, Math.round(canvas.clientWidth * ratio));
      canvas.height = Math.max(1, Math.round(canvas.clientHeight * ratio));
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform1f(aspect, canvas.width / canvas.height);
      resume();
    };
    const move = (event: PointerEvent) => {
      if (event.pointerType !== 'mouse') return;
      const bounds = stage.getBoundingClientRect();
      pointer.targetX = ((event.clientX - bounds.left) / bounds.width - 0.5) * 2;
      pointer.targetY = ((event.clientY - bounds.top) / bounds.height - 0.5) * 2;
    };
    const lost = (event: Event) => { event.preventDefault(); stopped = true; cancelAnimationFrame(frame); stage.removeAttribute('data-rendered'); };
    // shortcut: context loss uses static artwork; rebuild the scene if automatic GPU recovery is needed.
    const observer = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; if (visible) resume(); });
    const sizes = new ResizeObserver(resize);
    observer.observe(stage);
    sizes.observe(canvas);
    stage.parentElement?.addEventListener('pointermove', move);
    canvas.addEventListener('webglcontextlost', lost);
    document.addEventListener('visibilitychange', resume);
    reduced.addEventListener('change', resume);
    resize();
    return () => {
      stopped = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      sizes.disconnect();
      stage.parentElement?.removeEventListener('pointermove', move);
      canvas.removeEventListener('webglcontextlost', lost);
      document.removeEventListener('visibilitychange', resume);
      reduced.removeEventListener('change', resume);
      release();
    };
  }, []);

  return <div ref={stageRef} className="ribbon-stage" aria-hidden="true"><div className="ribbon-fallback"><span /><span /><span /><span /><span /><span /><span /></div><canvas ref={canvasRef} className="ribbon-canvas" /></div>;
}
