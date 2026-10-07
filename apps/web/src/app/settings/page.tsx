'use client';
import { useState } from 'react';
import ProfileSettings from '../workspace';
import AccountControls, { ReceiptStatus, type DeletionReceipt } from '../account-controls';
import { Screen, useLearner } from '../learner-context';
export default function Page() {
  const { profile, features, refresh } = useLearner();
  const [receipt, setReceipt] = useState<DeletionReceipt | null>(null);
  return receipt ? <section className="screen"><h1 tabIndex={-1}>Your deletion receipt</h1><ReceiptStatus initial={receipt} /></section>
    : <Screen title="Your account, your choices"><ProfileSettings />{profile && <AccountControls csrfToken={profile.csrf_token} remindersEnabled={Boolean(features?.reminders)} onDeleted={value => { setReceipt(value); void refresh(); }} />}</Screen>;
}
