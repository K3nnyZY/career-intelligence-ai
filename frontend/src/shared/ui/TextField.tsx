import { useId } from 'react';
import type { ComponentProps } from 'react';

type Props = ComponentProps<'textarea'> & { label: string; hint: string };

export function TextField({ label, hint, id: suppliedId, ...props }: Props) {
  const generatedId = useId();
  const id = suppliedId ?? generatedId;
  return <div className="mt-5">
    <label htmlFor={id} className="mb-2 block text-sm font-semibold">{label}</label>
    <textarea id={id} aria-describedby={`${id}-hint`} autoComplete="off" spellCheck={false}
      className="w-full resize-y rounded-lg border border-accent/30 bg-paper/40 p-4 text-sm leading-6 placeholder:text-muted/70 read-only:opacity-65" {...props} />
    <p id={`${id}-hint`} className="mt-2 text-xs leading-5 text-muted">{hint}</p>
  </div>;
}
