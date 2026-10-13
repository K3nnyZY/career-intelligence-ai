import type { ReactNode } from 'react';

interface Props { id: string; step: string; title: string; children: ReactNode; className?: string }

export function Panel({ id, step, title, children, className = '' }: Props) {
  return <section aria-labelledby={id} className={`min-w-0 rounded-2xl border border-line bg-white p-6 md:p-8 ${className}`}>
    <p className="text-xs font-bold tracking-[0.16em] text-accent">{step}</p>
    <h2 id={id} className="mt-2 mb-6 text-2xl leading-tight font-semibold tracking-tight">{title}</h2>
    {children}
  </section>;
}
