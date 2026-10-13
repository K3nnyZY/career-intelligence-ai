import type { ComponentProps } from 'react';

type Props = ComponentProps<'button'> & { variant?: 'primary' | 'secondary' };

export function Button({ variant = 'primary', className = '', children, ...props }: Props) {
  return <button type="button" className={`inline-flex items-center justify-center gap-2 rounded-lg px-5 py-3 text-sm font-semibold transition-colors disabled:opacity-45 ${variant === 'primary' ? 'bg-accent text-white hover:bg-accent/90' : 'border border-accent/25 bg-transparent text-ink hover:bg-white/60'} ${className}`} {...props}>{children}</button>;
}
