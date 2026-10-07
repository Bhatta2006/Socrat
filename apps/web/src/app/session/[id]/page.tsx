'use client';
import { useParams } from 'next/navigation';
import TodaySession from '../../learning-session';
import { Screen, useLearner } from '../../learner-context';
import { useEffect, useState } from 'react';
export default function Page() {
  const { profile, goal } = useLearner(); const { id } = useParams<{ id: string }>();
  const [revision, setRevision] = useState<number | null>(null); const [error, setError] = useState('');
  useEffect(() => { if (!goal) return; fetch(`/api/v1/goals/${goal.id}/curriculum`).then(async response => { if (!response.ok) throw new Error(); setRevision((await response.json()).revision); }).catch(() => setError('Review and confirm your plan before starting a session.')); }, [goal]);
  return <Screen title="One focused session" requireGoal>{error && <p role="alert">{error}</p>}{goal && profile && revision !== null && <TodaySession goalId={goal.id} csrfToken={profile.csrf_token} curriculumRevision={revision} sessionId={id} routed />}</Screen>;
}
