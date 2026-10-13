import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'EventPass · Promotion intelligence', description: 'Traceable public event promotions for AllEvents and Mepass.' };
export default function Layout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
