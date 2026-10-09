'use client';

import Link from 'next/link';
import { AlertTriangle, RotateCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty';

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto grid min-h-[60vh] max-w-xl place-items-center px-4" role="alert">
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon"><AlertTriangle /></EmptyMedia>
          <EmptyTitle>This page hit an error</EmptyTitle>
          <EmptyDescription>Your progress is saved. Try again, or head back to today&apos;s plan.</EmptyDescription>
        </EmptyHeader>
        <EmptyContent className="flex-row justify-center">
          <Button onClick={reset}><RotateCw data-icon="inline-start" /> Try again</Button>
          <Button asChild variant="outline"><Link href="/today">Today</Link></Button>
        </EmptyContent>
      </Empty>
    </div>
  );
}
