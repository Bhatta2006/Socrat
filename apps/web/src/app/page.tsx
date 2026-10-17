import localFont from 'next/font/local';
import { GeistMono } from 'geist/font/mono';
import { LandingPage } from '@/components/landing/landing-page';

// Landing display face (SIL OFL 1.1, vendored in src/fonts). Loaded on this route only.
const fraunces = localFont({
  src: [
    { path: '../fonts/fraunces-latin-standard-normal.woff2', style: 'normal' },
    { path: '../fonts/fraunces-latin-standard-italic.woff2', style: 'italic' },
  ],
  variable: '--font-fraunces',
  weight: '100 900',
  display: 'swap',
});

export default function Home() {
  return <LandingPage fontClassName={`${fraunces.variable} ${GeistMono.variable}`} />;
}
