'use client';
import { useState } from 'react';
import Onboarding from '../onboarding';
import ProfileSettings from '../workspace';
import { Screen, useLearner } from '../learner-context';
export default function Page() { const { profile, features } = useLearner(); const [ready, setReady] = useState(false); return <Screen title="A learning path that fits you">
  {!ready ? <><p className="lede">Begin with your profile. Then choose a goal and a comfortable pace.</p><ProfileSettings /><button className="btn btn-primary mt-4" disabled={!profile?.adult_confirmed} onClick={() => setReady(true)}>Continue to your learning goal</button></>
    : profile && <Onboarding csrfToken={profile.csrf_token} timezone={profile.timezone} adultConfirmed={profile.adult_confirmed} diagnosticsEnabled={Boolean(features?.diagnostics)} routed />}
</Screen>; }
