'use client';

import { LazyMotion, MotionConfig } from 'motion/react';
import type { ReactNode } from 'react';
import { useReducedMotion } from '@/lib/motion';

// Animation features load after first paint; components render with the small `m` component.
const features = () => import('./motion-features').then(mod => mod.default);

/** Honours the system preference and the in-app "Reduce motion" setting. */
export function MotionProvider({ children }: { children: ReactNode }) {
  const { reduced } = useReducedMotion();
  return (
    <MotionConfig reducedMotion={reduced ? 'always' : 'never'}>
      <LazyMotion features={features} strict>
        {children}
      </LazyMotion>
    </MotionConfig>
  );
}
