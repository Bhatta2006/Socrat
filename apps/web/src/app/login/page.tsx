import type { Features } from '@/lib/types';
import { LoginForm } from './login-form';

// Which sign-in options exist is server configuration; render it into the first HTML.
export const dynamic = 'force-dynamic';

async function features(): Promise<Features | null> {
  try {
    const base = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
    const response = await fetch(`${base}/api/v1/features`, { next: { revalidate: 300 }, signal: AbortSignal.timeout(1500) });
    return response.ok ? ((await response.json()) as Features) : null;
  } catch {
    return null; // the client asks again
  }
}

export default async function LoginPage() {
  return <LoginForm initialFeatures={await features()} />;
}
