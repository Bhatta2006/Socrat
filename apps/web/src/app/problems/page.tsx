import { redirect } from 'next/navigation';

/** Practice lives at /library; keep the obvious URL from dead-ending. */
export default function ProblemsIndex() {
  redirect('/library');
}
