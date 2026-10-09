import Link from 'next/link';
import { Compass } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty';

export default function NotFound() {
  return (
    <div className="mx-auto grid min-h-[60vh] max-w-xl place-items-center px-4">
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon"><Compass /></EmptyMedia>
          <EmptyTitle>That page doesn&apos;t exist</EmptyTitle>
          <EmptyDescription>The link may be old, or the page has moved.</EmptyDescription>
        </EmptyHeader>
        <EmptyContent><Button asChild><Link href="/">Go home</Link></Button></EmptyContent>
      </Empty>
    </div>
  );
}
