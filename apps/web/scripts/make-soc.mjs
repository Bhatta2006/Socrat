// Renders Soc's avatar from scripts/soc-source.webp: the white backdrop becomes transparent
// (flood-filled from the edges, so the white of the eyes stays), then it is trimmed to a
// square and saved at the sizes the app uses. Run from apps/web: node scripts/make-soc.mjs
import sharp from 'sharp';

const { data, info } = await sharp('scripts/soc-source.webp').ensureAlpha().raw().toBuffer({ resolveWithObject: true });
const { width: w, height: h } = info;
const light = i => data[i] > 232 && data[i + 1] > 232 && data[i + 2] > 232;
const seen = new Uint8Array(w * h);
const stack = [];
for (let x = 0; x < w; x++) stack.push(x, (h - 1) * w + x);
for (let y = 0; y < h; y++) stack.push(y * w, y * w + w - 1);
while (stack.length) {
  const p = stack.pop();
  if (seen[p] || !light(p * 4)) continue;
  seen[p] = 1;
  data[p * 4 + 3] = 0;
  const x = p % w, y = (p - x) / w;
  if (x > 0) stack.push(p - 1);
  if (x < w - 1) stack.push(p + 1);
  if (y > 0) stack.push(p - w);
  if (y < h - 1) stack.push(p + w);
}
// Soften the cut edge: near-white pixels touching the backdrop get partial alpha.
for (let p = 0; p < w * h; p++) {
  if (seen[p]) continue;
  const i = p * 4, x = p % w;
  const edge = (x > 0 && seen[p - 1]) || (x < w - 1 && seen[p + 1]) || seen[p - w] || seen[p + w];
  if (edge) data[i + 3] = Math.min(data[i + 3], 255 - Math.max(0, Math.min(data[i], data[i + 1], data[i + 2]) - 150) * 2);
}
const clean = await sharp(data, { raw: info }).png().toBuffer();
const trimmed = await sharp(clean).trim({ threshold: 1 }).toBuffer({ resolveWithObject: true });
const side = Math.max(trimmed.info.width, trimmed.info.height);
const square = await sharp(trimmed.data)
  .extend({
    top: Math.floor((side - trimmed.info.height) / 2), bottom: Math.ceil((side - trimmed.info.height) / 2),
    left: Math.floor((side - trimmed.info.width) / 2), right: Math.ceil((side - trimmed.info.width) / 2),
    background: { r: 0, g: 0, b: 0, alpha: 0 },
  })
  .png().toBuffer();
for (const size of [96, 192, 384]) {
  await sharp(square).resize(size, size).webp({ quality: 90, alphaQuality: 100 }).toFile(`public/soc/soc-${size}.webp`);
  console.log(`public/soc/soc-${size}.webp`);
}
