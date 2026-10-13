'use client';

import { MotionConfig } from 'motion/react';
import type { ReactNode } from 'react';

/** Every Motion animation honours the learner's "reduce motion" setting. */
export function MotionProvider({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user">{children}</MotionConfig>;
}
