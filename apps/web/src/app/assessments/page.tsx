'use client';
import AssessmentFlow from '../assessment';
import { Screen, useLearner } from '../learner-context';
export default function Page() { const { profile, goal } = useLearner(); return <Screen title="Prove what stays with you" requireGoal>{goal && profile && <AssessmentFlow goalId={goal.id} csrfToken={profile.csrf_token} />}</Screen>; }
