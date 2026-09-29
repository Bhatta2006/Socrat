import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'Socrat — Learning workspace',
  description: 'A deterministic-first learning platform. DSA first, more skills to come.',
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en" data-theme="wireframe"><body>{children}</body></html>;
}
