'use client';
export default function Error({ reset }: { error: Error; reset: () => void }) { return <section className="screen"><h1 tabIndex={-1}>Your work is preserved</h1><p role="alert">The workspace could not load this screen. No mastery change was made.</p><button className="btn btn-primary" onClick={reset}>Try again</button></section>; }
