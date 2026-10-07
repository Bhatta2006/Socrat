'use client';
import Planner from '../planner';
import { Screen, useLearner } from '../learner-context';
export default function Page() { const { profile, goal } = useLearner(); return <Screen title="Your learning plan" requireGoal>{goal && profile && <Planner goalId={goal.id} csrfToken={profile.csrf_token} routed />}</Screen>; }
