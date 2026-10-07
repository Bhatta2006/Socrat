'use client';
import Link from 'next/link';
import DiagnosticFlow from '../diagnostic';
import { Screen, useLearner } from '../learner-context';
export default function Page() { const { profile, goal, features } = useLearner(); return <Screen title="Find your starting point" requireGoal>{goal && profile && <DiagnosticFlow goalId={goal.id} csrfToken={profile.csrf_token} enabled={Boolean(features?.diagnostics)} routed />}<Link href="/plan" className="btn">Review your plan</Link></Screen>; }
