import type { Metadata, Viewport } from 'next';
import localFont from 'next/font/local';
import { GeistSans } from 'geist/font/sans';
import './globals.css';
import { SessionProvider } from '@/lib/session';
import { REDUCE_MOTION_SCRIPT } from '@/lib/motion';
import Shell from '@/components/shell';
import { ThemeProvider } from '@/components/theme-provider';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Toaster } from '@/components/ui/sonner';
import { WebVitals } from '@/components/web-vitals';

// Body and UI (SIL OFL 1.1, vendored in src/fonts). Display uses Geist Sans Bold.
const figtree = localFont({
  src: '../fonts/figtree-latin-wght.woff2',
  variable: '--font-figtree',
  weight: '300 900',
  display: 'swap',
});
const jetbrains = localFont({
  src: '../fonts/jetbrains-mono-latin-wght.woff2',
  variable: '--font-jetbrains',
  weight: '100 800',
  display: 'swap',
  preload: false,
});

export const metadata: Metadata = {
  title: { default: 'Socrat', template: '%s · Socrat' },
  description: 'Learn it. Then prove it. A personal programming tutor for learning to code, interview preparation and contests.',
  robots: { index: false, follow: false },
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#F6F4FA' },
    { media: '(prefers-color-scheme: dark)', color: '#0F0E14' },
  ],
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${figtree.variable} ${jetbrains.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: REDUCE_MOTION_SCRIPT }} />
      </head>
      <body>
        <WebVitals />
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
          <TooltipProvider delayDuration={200}>
            <SessionProvider>
              <Shell>{children}</Shell>
            </SessionProvider>
            <Toaster closeButton position="bottom-right" />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
