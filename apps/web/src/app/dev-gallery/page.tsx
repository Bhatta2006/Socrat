import { notFound } from 'next/navigation';
import Gallery from './gallery';

export const metadata = { title: 'Component gallery' };

/** Development-only review surface for every component in both themes; 404 in production. */
export default function GalleryPage() {
  if (process.env.NODE_ENV === 'production') notFound();
  return <Gallery />;
}
