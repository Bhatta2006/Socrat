'use client';

import { LazyMotion, MotionConfig } from 'motion/react';
import type { ReactNode } from 'react';

// Animation features load after first paint; pages render with the small `m` component.
const features = () => import('./motion-features').then(mod => mod.default);

/** For pages that use Motion: honours "reduce motion" and keeps Motion out of the shared bundle. */
export function MotionProvider({ children }: { children: ReactNode }) {
  return (
    <MotionConfig reducedMotion="user">
      <LazyMotion features={features} strict>
        {children}
      </LazyMotion>
    </MotionConfig>
  );
}
