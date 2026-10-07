import Link from 'next/link';
export default function NotFound() { return <section className="screen"><h1 tabIndex={-1}>Find your next step</h1><p>This page could not be found. Your saved learning is still here.</p><Link className="btn btn-primary" href="/today">Go to Today</Link></section>; }
