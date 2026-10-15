import Link from 'next/link';
import { Illustration } from '@/components/socrat/illustration';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <div className="mx-auto grid min-h-[60dvh] max-w-xl place-items-center px-4 py-16">
      <div className="grid justify-items-center gap-4 text-center">
        <Illustration name="empty" className="size-32" />
        <h1 className="type-display-m">That page does not exist</h1>
        <p className="text-base text-muted-foreground">The link may be old, or the page has moved.</p>
        <Button asChild className="mt-2"><Link href="/">Go home</Link></Button>
      </div>
    </div>
  );
}
