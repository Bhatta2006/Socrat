// Renders the installable-app icons from the Socrat mark (src/app/icon.svg's design).
// Run from apps/web after changing the mark: node scripts/make-icons.mjs
import sharp from 'sharp';

const mark = (size, pad) => {
  const inner = size - pad * 2;
  const s = inner / 32;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
<rect width="${size}" height="${size}" rx="${pad ? 0 : size * 0.28}" fill="#0E0D14"/>
<g transform="translate(${pad} ${pad}) scale(${s})"><path d="M16 4.5a6.25 6.25 0 0 0 0 12.5Z" fill="#7D39EB"/><path d="M16 15a6.25 6.25 0 0 1 0 12.5Z" fill="#F4F2FA"/></g></svg>`;
};

const out = [
  ['icon-192.png', 192, 0],
  ['icon-512.png', 512, 0],
  ['maskable-512.png', 512, 96], // keeps the mark inside the safe zone
  ['apple-touch-icon.png', 180, 18],
];
for (const [name, size, pad] of out) {
  await sharp(Buffer.from(mark(size, pad))).png().toFile(`public/icons/${name}`);
  console.log(`public/icons/${name}`);
}
